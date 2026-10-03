# services/delivery_service.py
"""
Delivery service — local operations only.

Responsibilities (strictly local):
  - validations (status enums, transition legality, address existence)
  - model construction (Delivery)
  - persistence via repositories
  - entity-level helpers (dict conversion, subscriber payloads)

NOT responsible for:
  - calling the order workflow             → delivery_workflow.py
  - calling the inventory silo             → delivery_workflow.py
  - state transitions gated by policy      → delivery_workflow.py
  - cross-entity side effects (order
    advancement, inventory confirmation)   → delivery_workflow.py

No `OrderService`, no `OrderWorkflow`, no remote clients on this class.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from core.models.api_models import Delivery_API, DeliveryStatus, DeliveryUpdate_API
from core.exceptions.specific.delivery_exceptions import (
    DeliveryNotFoundException,
    DeliveryCreationFailedException,
    DeliveryUpdateFailedException,
    DeliveryDeleteFailedException,
    DeliveryValidationFailedException,
    DeliveryCannotBeUpdatedException,
    DeliveryBulkUpdateFailedException,
    DeliveryBulkDeleteFailedException,
    DeliveryStatusInvalidException,
    AddressNotFoundException,
    DeliveryAlreadyDeliveredException,
)
from core.models.models import Delivery
from repositories.delivery_repository import DeliveryRepository
from repositories.address_repository import AddressRepository
from services.location_service import LocationService

from core.logging_config import get_logger

logger = get_logger(__name__)



class DeliveryService:
    """Service for delivery-related local business logic."""

    # Valid delivery statuses — mirrors the DB enum.
    VALID_STATUSES = [
        'pending', 'processing', 'confirmed', 'shipped',
        'in_transit', 'out_for_delivery', 'delivered',
        'failed', 'cancelled', 'returned', 'refunded',
    ]

    # Statuses that cannot be modified.
    FROZEN_STATUSES = ['delivered', 'cancelled', 'returned', 'refunded']

    def __init__(self):
        self.delivery_repo = DeliveryRepository()
        self.address_repo = AddressRepository()
        self.location_service = LocationService()

    # ==================== Validation helpers ====================

    def validate_delivery_data(
        self, delivery_data: Delivery_API, is_update: bool = False
    ) -> None:
        """Validate delivery data before creation or update."""

        if (
            delivery_data.delivery_total_weight is not None
            and delivery_data.delivery_total_weight < 0
        ):
            raise DeliveryValidationFailedException(
                field="delivery_total_weight",
                value=delivery_data.delivery_total_weight,
                reason="Delivery weight cannot be negative",
            )

        if delivery_data.delivery_package_count is not None:
            try:
                count = int(delivery_data.delivery_package_count)
                if count < 0:
                    raise DeliveryValidationFailedException(
                        field="delivery_package_count",
                        value=delivery_data.delivery_package_count,
                        reason="Package count cannot be negative",
                    )
            except (ValueError, TypeError):
                raise DeliveryValidationFailedException(
                    field="delivery_package_count",
                    value=delivery_data.delivery_package_count,
                    reason="Package count must be a valid integer",
                )

        if (
            delivery_data.delivery_fee is not None
            and delivery_data.delivery_fee < 0
        ):
            raise DeliveryValidationFailedException(
                field="delivery_fee",
                value=delivery_data.delivery_fee,
                reason="Delivery fee cannot be negative",
            )

        if not is_update and delivery_data.delivery_status:
            if delivery_data.delivery_status.value not in self.VALID_STATUSES:
                raise DeliveryStatusInvalidException(
                    requested_status=delivery_data.delivery_status.value,
                    allowed_statuses=self.VALID_STATUSES,
                )

        if not is_update:
            has_recipient = (
                (delivery_data.recipient_person and delivery_data.recipient_person != 0)
                or (delivery_data.recipient_provider and delivery_data.recipient_provider != 0)
                or (delivery_data.delivery_invoice_ref and delivery_data.delivery_invoice_ref != 0)
            )
            if not has_recipient:
                raise DeliveryValidationFailedException(
                    field="recipient",
                    reason="Either recipient person, provider, or invoice reference is required",
                )

        if delivery_data.delivery_source_type:
            valid_source_types = ['cart', 'placed_order']
            if delivery_data.delivery_source_type.value not in valid_source_types:
                raise DeliveryValidationFailedException(
                    field="delivery_source_type",
                    value=delivery_data.delivery_source_type.value,
                    reason=f"Source type must be one of: {', '.join(valid_source_types)}",
                )

        if delivery_data.delivery_shipping_method:
            valid_methods = [
                'standard', 'express', 'overnight', 'pickup',
                'courier', 'same_day', 'international',
            ]
            if delivery_data.delivery_shipping_method.value not in valid_methods:
                raise DeliveryValidationFailedException(
                    field="delivery_shipping_method",
                    value=delivery_data.delivery_shipping_method.value,
                    reason=f"Shipping method must be one of: {', '.join(valid_methods)}",
                )

    def validate_status_transition(
        self, current_status: str, new_status: str
    ) -> bool:
        """
        Local, non-policy status transition validation.

        Kept for the non-workflow callers that just want to write a
        status column. New code should go through DeliveryWorkflow,
        which consults DeliveryPolicy instead.
        """
        current = (current_status or '').lower()
        new = (new_status or '').lower()

        if current == new:
            return True

        if current in self.FROZEN_STATUSES:
            raise DeliveryCannotBeUpdatedException(
                delivery_id=None,
                current_status=current,
                attempted_action=f"change status to {new}",
                allowed_actions=["view"],
            )

        # Local transitions table — kept in sync with DeliveryPolicy,
        # but this is the *fallback* used by callers that don't go
        # through the workflow.
        allowed_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['confirmed', 'cancelled'],
            'confirmed': ['shipped', 'cancelled'],
            'shipped': ['in_transit', 'cancelled'],
            'in_transit': ['out_for_delivery', 'failed', 'returned'],
            'out_for_delivery': ['delivered', 'failed', 'returned'],
            'failed': ['pending', 'cancelled'],
            'returned': ['pending', 'processing'],
            'delivered': [],
            'cancelled': [],
            'refunded': [],
        }

        allowed = allowed_transitions.get(current, [])
        if new not in allowed:
            raise DeliveryStatusInvalidException(
                requested_status=new,
                allowed_statuses=allowed,
            )
        return True

    # ==================== Model building ====================

    def build_delivery_model(
        self,
        delivery_data: Delivery_API,
        existing_delivery: Optional[Delivery] = None,
    ) -> Delivery:
        """Build or update a Delivery model from API data."""

        if existing_delivery:
            delivery = existing_delivery
            logger.debug(f"Updating existing delivery {delivery.id_delivery}")
        else:
            delivery = Delivery()
            delivery.delivery_created_at = datetime.now()
            logger.debug("Creating new delivery")

        if delivery_data.delivery_package_count is not None:
            delivery.delivery_package_count = delivery_data.delivery_package_count

        if delivery_data.delivery_total_weight is not None:
            delivery.delivery_total_weight = delivery_data.delivery_total_weight

        if delivery_data.delivery_cargo_dimensions is not None:
            delivery.delivery_cargo_dimensions = delivery_data.delivery_cargo_dimensions
            delivery.delivery_package_count = len(delivery.delivery_cargo_dimensions.split(','))

        if delivery_data.delivery_goods_description is not None:
            delivery.delivery_goods_description = delivery_data.delivery_goods_description

        if delivery_data.hs_code is not None:
            delivery.hs_code = delivery_data.hs_code

        if delivery_data.delivery_merchant_name is not None:
            delivery.delivery_merchant_name = delivery_data.delivery_merchant_name

        if delivery_data.delivery_shipping_method is not None:
            delivery.delivery_shipping_method = delivery_data.delivery_shipping_method.value

        if delivery_data.delivery_special_instructions is not None:
            delivery.delivery_special_instructions = delivery_data.delivery_special_instructions

        # Status is set verbatim here. Policy validation belongs to the
        # workflow. This keeps the service usable by code paths that
        # don't care about the state machine (e.g. bulk imports).
        if delivery_data.delivery_status is not None:
            delivery.delivery_status = delivery_data.delivery_status.value
        elif not existing_delivery:
            delivery.delivery_status = 'pending'

        if delivery_data.delivery_fee is not None:
            delivery.delivery_fee = delivery_data.delivery_fee

        if delivery_data.recipient_person is not None:
            delivery.recipient_person = delivery_data.recipient_person

        if delivery_data.recipient_provider is not None:
            delivery.recipient_provider = delivery_data.recipient_provider

        if delivery_data.delivery_broker_id is not None:
            delivery.delivery_broker_id = delivery_data.delivery_broker_id

        if delivery_data.delivery_provider_id is not None:
            delivery.delivery_provider_id = delivery_data.delivery_provider_id

        if delivery_data.delivery_invoice_ref is not None:
            delivery.delivery_invoice_ref = delivery_data.delivery_invoice_ref

        if delivery_data.delivery_source_type is not None:
            delivery.delivery_source_type = delivery_data.delivery_source_type.value

        if delivery_data.delivery_source_id is not None:
            delivery.delivery_source_id = delivery_data.delivery_source_id

        if (
            delivery_data.delivery_address_id is not None
            and delivery_data.delivery_address_id != 0
        ):
            address = self.address_repo.get_address_by_id(
                delivery_data.delivery_address_id
            )
            if address is None:
                raise AddressNotFoundException(
                    address_id=delivery_data.delivery_address_id
                )
            delivery.delivery_address_id = delivery_data.delivery_address_id

        if (
            delivery_data.delivery_current_address_id is not None
            and delivery_data.delivery_current_address_id != 0
        ):
            current_address = self.address_repo.get_address_by_id(
                delivery_data.delivery_current_address_id
            )
            if current_address is None:
                raise AddressNotFoundException(
                    address_id=delivery_data.delivery_current_address_id
                )
            delivery.delivery_current_address_id = (
                delivery_data.delivery_current_address_id
            )

        delivery.delivery_updated_at = datetime.now()
        return delivery

    # ==================== CRUD (local only) ====================

    def get_delivery_by_id(
        self, delivery_id: int, eager_load: bool = True
    ) -> Delivery:
        delivery = self.delivery_repo.get_by_id(delivery_id, eager_load)
        if not delivery:
            logger.warning(f"Delivery not found with ID: {delivery_id}")
            raise DeliveryNotFoundException(delivery_id=delivery_id)
        return delivery

    def get_all_deliveries(
        self,
        provider_id: int = 0,
        order_id: int = 0,
        broker_id: int = 0,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Delivery]:
        return self.delivery_repo.get_all(
            provider_id, order_id, broker_id, offset, limit
        )

    def get_deliveries_by_status(self, status: str) -> List[Delivery]:
        status_lower = (status or '').lower()
        if status_lower not in self.VALID_STATUSES:
            raise DeliveryStatusInvalidException(
                requested_status=status,
                allowed_statuses=self.VALID_STATUSES,
            )
        return self.delivery_repo.get_by_status(status_lower)

    def create_delivery(self, delivery_data: Delivery_API) -> Delivery:
        """
        Create a delivery. Local only.

        Callers that need policy-validated status entry points (e.g.
        creating a delivery that isn't in `pending`) should go through
        DeliveryWorkflow.create_delivery.
        """
        logger.info(
            f"Creating new delivery for source: "
            f"{delivery_data.delivery_source_type} "
            f"{delivery_data.delivery_source_id}"
        )
        self.validate_delivery_data(delivery_data, is_update=False)
        delivery = self.build_delivery_model(delivery_data)

        try:
            result = self.delivery_repo.create(delivery)
            logger.info(
                f"Delivery created successfully with ID: "
                f"{result.id_delivery}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create delivery: {e}")
            raise DeliveryCreationFailedException(
                error=str(e),
                order_id=delivery_data.delivery_source_id,
                provider_id=delivery_data.delivery_provider_id,
            )

    def update_delivery(
        self, delivery_id: int, delivery_data: Delivery_API
    ) -> Delivery:
        """
        Update a delivery's mutable fields. Local only.

        Does NOT consult DeliveryPolicy. Callers that need a
        policy-gated status change must call
        DeliveryWorkflow.transition_status.
        """
        logger.info(f"Updating delivery with ID: {delivery_id}")

        existing = self.get_delivery_by_id(delivery_id)
        self.validate_delivery_data(delivery_data, is_update=True)
        updated = self.build_delivery_model(delivery_data, existing)

        try:
            return self.delivery_repo.update(updated)
        except Exception as e:
            logger.error(f"Failed to update delivery {delivery_id}: {e}")
            raise DeliveryUpdateFailedException(
                delivery_id=delivery_id, error=str(e)
            )

    def persist_delivery(self, delivery: Delivery) -> Delivery:
        """Local: write the delivery row. Used by the workflow."""
        # delivery.delivery_updated_at = datetime.now()
        return self.delivery_repo.update(delivery)

    def delete_delivery(
        self, delivery_id: int, force_delete: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a delivery. Local only.

        Cross-entity side effects (releasing inventory, refunding a
        payment) are the workflow's job. Callers that need them must
        go through DeliveryWorkflow.delete_delivery.
        """
        logger.info(
            f"Deleting delivery with ID: {delivery_id} "
            f"(force={force_delete})"
        )

        existing = self.get_delivery_by_id(delivery_id)

        deletable_statuses = ['pending', 'cancelled', 'failed']
        if (
            not force_delete
            and existing.delivery_status not in deletable_statuses
        ):
            raise DeliveryDeleteFailedException(
                delivery_id=delivery_id,
                error=(
                    f"Cannot delete delivery with status: "
                    f"{existing.delivery_status}. "
                    f"Use force_delete=True to override."
                ),
            )

        success = self.delivery_repo.delete(existing)
        if not success:
            raise DeliveryDeleteFailedException(
                delivery_id=delivery_id,
                error="Repository returned False",
            )

        logger.info(f"Delivery {delivery_id} deleted successfully")
        return {
            "success": True,
            "message": "Delivery deleted successfully",
            "delivery_id": delivery_id,
        }

    # ==================== Bulk (local) ====================

    def bulk_delete_deliveries(
        self,
        provider_id: int = 0,
        order_id: int = 0,
        status: str = None,
        force_delete: bool = False,
    ) -> Dict[str, Any]:
        logger.info(
            f"Bulk deleting deliveries - provider:{provider_id}, "
            f"order:{order_id}, status:{status}, force:{force_delete}"
        )
        try:
            status_lower = status.lower() if status else None
            deleted_count = self.delivery_repo.bulk_delete_by_criteria(
                provider_id, order_id, status_lower, force_delete
            )
            return {
                "success": True,
                "message": f"Deleted {deleted_count} deliveries",
                "deleted_count": deleted_count,
                "filters": {
                    "provider_id": provider_id if provider_id > 0 else None,
                    "order_id": order_id if order_id > 0 else None,
                    "status": status_lower,
                    "force_delete": force_delete,
                },
            }
        except Exception as e:
            logger.error(f"Failed to bulk delete deliveries: {e}")
            raise DeliveryBulkDeleteFailedException(
                provider_id=provider_id if provider_id > 0 else None,
                order_id=order_id if order_id > 0 else None,
                status=status,
                details={"error": str(e), "force_delete": force_delete},
            )

    def update_status_local(
        self, delivery_id: int, new_status: str
    ) -> Delivery:
        """
        Local status write used by the workflow after the policy has
        approved the transition. No policy check here.
        """
        delivery = self.get_delivery_by_id(delivery_id)
        delivery.delivery_status = new_status.lower()
        delivery.delivery_updated_at = datetime.now()
        return self.delivery_repo.update(delivery)

    def bulk_update_status_local(
        self, delivery_ids: List[int], new_status: str
    ) -> List[Delivery]:
        """Local status write for a batch. Callers must pre-validate."""
        status_lower = new_status.lower()
        if status_lower not in self.VALID_STATUSES:
            raise DeliveryStatusInvalidException(
                requested_status=new_status,
                allowed_statuses=self.VALID_STATUSES,
            )

        updated: List[Delivery] = []
        failed: List[Dict[str, Any]] = []
        for delivery_id in delivery_ids:
            try:
                updated.append(
                    self.update_status_local(delivery_id, status_lower)
                )
            except Exception as e:
                failed.append(
                    {"delivery_id": delivery_id, "error": str(e)}
                )

        if failed:
            raise DeliveryBulkUpdateFailedException(
                delivery_ids=delivery_ids,
                target_status=status_lower,
                success_count=len(updated),
                failed_count=len(failed),
                failed_ids=[f["delivery_id"] for f in failed],
                errors=failed,
            )
        return updated

    # ==================== Stats (local) ====================

    def get_delivery_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {"total": 0, "by_status": {}}
        for status in self.VALID_STATUSES:
            count = self.delivery_repo.count_by_status(status)
            stats["by_status"][status] = count
            stats["total"] += count
        return stats

    # ==================== Subscriber payload (local) ====================

    def delivery_to_dict(self, delivery: Delivery) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in delivery.__dict__.items():
            if key.startswith("_"):
                continue
            if hasattr(value, "isoformat"):
                out[key] = value.isoformat()
            elif hasattr(value, "id"):
                out[key] = value.id
            else:
                out[key] = value
        return out

    # ==================== Address helpers (local) ====================

    def validate_address_exists(self, address_id: int) -> None:
        if self.address_repo.get_address_by_id(address_id) is None:
            raise AddressNotFoundException(address_id=address_id)