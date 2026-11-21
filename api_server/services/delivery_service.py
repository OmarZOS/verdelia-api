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

from repositories.order_repository import OrderItemRepository
from core.models.api_models import (
    Delivery_API,
    DeliveryStatus,
    DeliveryUpdate_API,
    OrderedItem_API,
)
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
        self.order_item_repo = OrderItemRepository()

    # ==================== Validation helpers ====================

    def validate_delivery_data(
        self, delivery_data: Delivery_API, is_update: bool = False,
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

        # Recipient check on create. `has_recipient` in the policy
        # accepts any of these four; the validation mirrors that so
        # the caller isn't forced to pass a person id when the
        # delivery is a provider-initiated one.
        if not is_update:
            has_recipient = any((
                (delivery_data.recipient_person or 0) > 0,
                (delivery_data.recipient_provider or 0) > 0,
                (delivery_data.delivery_address_id or 0) > 0,
                (delivery_data.delivery_current_address_id or 0) > 0,
                (delivery_data.delivery_invoice_ref or 0) > 0,
            ))
            if not has_recipient:
                raise DeliveryValidationFailedException(
                    field="recipient",
                    reason=(
                        "At least one of recipient_person, "
                        "recipient_provider, delivery_address_id, "
                        "delivery_current_address_id, or "
                        "delivery_invoice_ref is required"
                    ),
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
        self, current_status: str, new_status: str,
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
        """
        Build or update a `Delivery` model from API data.

        The API field names (`delivery_address_id`,
        `recipient_person`, `delivery_special_instructions`, …) are
        mapped to the model's *column* names (`address_id`,
        `recipient_person_id`, `special_instructions`, …). The
        service owns that mapping; the workflow's
        `_apply_body_to_instance` owns a different, partial mapping
        for the PATCH path, and the two are deliberately kept
        separate — this method handles full construction, the
        workflow's method handles partial patches.
        """
        if existing_delivery:
            delivery = existing_delivery
            logger.debug("Updating existing delivery %s", delivery.id_delivery)
        else:
            delivery = Delivery()
            delivery.created_at = datetime.now()
            logger.debug("Creating new delivery")

        if delivery_data.delivery_package_count is not None:
            delivery.delivery_package_count = delivery_data.delivery_package_count

        if delivery_data.delivery_total_weight is not None:
            delivery.delivery_total_weight = delivery_data.delivery_total_weight

        if delivery_data.delivery_cargo_dimensions is not None:
            delivery.delivery_cargo_dimensions = delivery_data.delivery_cargo_dimensions
            # Package count inferred from the dimensions string when
            # the caller didn't set an explicit count. Splitting on
            # commas means "LxWxH" yields 1 and "box1,box2,box3"
            # yields 3 — a legacy heuristic kept for compatibility.
            delivery.delivery_package_count = len(
                delivery.delivery_cargo_dimensions.split(',')
            )

        if delivery_data.delivery_goods_description is not None:
            delivery.delivery_goods_description = (
                delivery_data.delivery_goods_description
            )

        if delivery_data.delivery_broker_id is not None:
            delivery.delivery_broker_id = delivery_data.delivery_broker_id

        if delivery_data.hs_code is not None:
            delivery.hs_code = delivery_data.hs_code

        if delivery_data.delivery_shipping_method is not None:
            delivery.delivery_shipping_method = (
                delivery_data.delivery_shipping_method.value
            )

        if delivery_data.delivery_special_instructions is not None:
            delivery.special_instructions = (
                delivery_data.delivery_special_instructions
            )

        # Status is set verbatim here. Policy validation belongs to
        # the workflow.
        if delivery_data.delivery_status is not None:
            delivery.delivery_status = delivery_data.delivery_status.value
        elif not existing_delivery:
            delivery.delivery_status = 'pending'

        if delivery_data.delivery_fee is not None:
            delivery.delivery_fee = delivery_data.delivery_fee

        # API name → column name. Both point at the *same* physical
        # column but differ in naming convention.
        if delivery_data.recipient_person is not None:
            delivery.recipient_person_id = delivery_data.recipient_person
        if delivery_data.recipient_provider is not None:
            delivery.recipient_provider_id = delivery_data.recipient_provider
        if delivery_data.carrying_user_id is not None:
            delivery.carrying_user_id = delivery_data.carrying_user_id
        if delivery_data.delivery_provider_id is not None:
            delivery.delivery_provider_id = delivery_data.delivery_provider_id
        if delivery_data.delivery_invoice_ref is not None:
            delivery.delivery_invoice_ref = delivery_data.delivery_invoice_ref

        if delivery_data.delivery_source_type is not None:
            delivery.delivery_source_type = (
                delivery_data.delivery_source_type.value
            )

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
            delivery.address_id = delivery_data.delivery_address_id

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
            delivery.current_address_id = (
                delivery_data.delivery_current_address_id
            )

        delivery.updated_at = datetime.now()
        return delivery

    # ==================== CRUD (local only) ====================

    def get_delivery_by_id(
        self, delivery_id: int, eager_load: bool = True,
    ) -> Delivery:
        delivery = self.delivery_repo.get_by_id(delivery_id, eager_load)
        if not delivery:
            logger.warning("Delivery not found with ID: %s", delivery_id)
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
            provider_id, order_id, broker_id, offset, limit,
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
        Create a delivery and attach the supplied ordered items.

        Two-phase write, with rollback on partial failure:

          1. Persist the delivery row (gets `id_delivery`).
          2. For every item in `delivery_data.delivery_ordered_items`,
             set `OrderedItem.delivery_id` and persist.
          3. If step 2 fails partway, unlink the items that were
             already linked, then delete the delivery row.

        The item update runs *after* the delivery insert because
        `delivery_id` doesn't exist until then. Unlinking on failure
        is what makes the rollback meaningful — a delivery that
        vanishes while its items still reference it is worse than a
        delivery that refuses to be created.
        """
        logger.info(
            "Creating delivery for source %s %s",
            delivery_data.delivery_source_type,
            delivery_data.delivery_source_id,
        )
        self.validate_delivery_data(delivery_data, is_update=False)

        # Detach the items list before building the delivery —
        # `Delivery_API.delivery_ordered_items` is a convenience
        # field, not a column.
        items_to_link = list(delivery_data.delivery_ordered_items or [])

        delivery = self.build_delivery_model(delivery_data)

        try:
            created = self.delivery_repo.create(delivery)
            logger.info("Delivery created with ID %s", created.id_delivery)
        except Exception as e:
            logger.error("Failed to create delivery: %s", e)
            raise DeliveryCreationFailedException(
                error=str(e),
                order_id=delivery_data.delivery_source_id,
                provider_id=delivery_data.delivery_provider_id,
            )

        # Link items. `_link_items_to_delivery` returns the ids it
        # successfully linked, so we can unlink them if the next one
        # fails.
        if items_to_link:
            linked_ids: List[int] = []
            try:
                linked_ids = self._link_items_to_delivery(
                    created.id_delivery, items_to_link,
                )
            except Exception as e:
                logger.error(
                    "Failed to link items to delivery %s: %s",
                    created.id_delivery, e,
                )
                # Unlink whatever was linked, then delete the row.
                self._unlink_items(linked_ids)
                try:
                    self.delivery_repo.delete(created)
                except Exception:
                    logger.exception(
                        "Failed to roll back delivery %s after link "
                        "failure", created.id_delivery,
                    )
                raise DeliveryCreationFailedException(
                    error=f"Item linking failed: {e}",
                    order_id=delivery_data.delivery_source_id,
                    provider_id=delivery_data.delivery_provider_id,
                )

        return created

    def _link_items_to_delivery(
        self,
        delivery_id: int,
        items: List[OrderedItem_API],
    ) -> List[int]:
        """
        Set `delivery_id` on each item and persist. Skips items
        without an `id_ordered_item` — those haven't been persisted
        yet, and this method only reassigns existing rows.

        Returns the list of item ids that were successfully linked.
        Callers use it to unlink on partial failure.
        """
        linked_ids: List[int] = []
        for api_item in items:
            item_id = getattr(api_item, "id_ordered_item", 0) or 0
            if item_id <= 0:
                logger.warning(
                    "Skipping item without id when linking to "
                    "delivery %s: %r", delivery_id, api_item,
                )
                continue

            existing = self.order_item_repo.get_by_id(item_id)
            if existing is None:
                logger.warning(
                    "OrderedItem %s not found while linking to "
                    "delivery %s", item_id, delivery_id,
                )
                continue

            existing.delivery_id = delivery_id
            self.order_item_repo.update(existing)
            linked_ids.append(item_id)
            logger.info(
                "OrderedItem %s linked to delivery %s",
                item_id, delivery_id,
            )
        return linked_ids

    def _unlink_items(self, item_ids: List[int]) -> None:
        """Best-effort: set `delivery_id` back to null on the given items."""
        for item_id in item_ids:
            try:
                existing = self.order_item_repo.get_by_id(item_id)
                if existing is None:
                    continue
                existing.delivery_id = None
                self.order_item_repo.update(existing)
                logger.info(
                    "OrderedItem %s unlinked from its delivery",
                    item_id,
                )
            except Exception:
                logger.exception(
                    "Failed to unlink OrderedItem %s during rollback",
                    item_id,
                )

    def update_delivery(
        self, delivery_id: int, delivery_data: Delivery_API,
    ) -> Delivery:
        """
        Update a delivery's mutable fields. Local only.

        Does NOT consult DeliveryPolicy. Callers that need a
        policy-gated status change must call
        DeliveryWorkflow.transition.
        """
        logger.info("Updating delivery with ID: %s", delivery_id)

        existing = self.get_delivery_by_id(delivery_id)
        self.validate_delivery_data(delivery_data, is_update=True)
        updated = self.build_delivery_model(delivery_data, existing)

        try:
            return self.delivery_repo.update(updated)
        except Exception as e:
            logger.error("Failed to update delivery %s: %s", delivery_id, e)
            raise DeliveryUpdateFailedException(
                delivery_id=delivery_id, error=str(e),
            )

    def persist_delivery(self, delivery: Delivery) -> Delivery:
        """Local: write the delivery row. Used by the workflow."""
        return self.delivery_repo.update(delivery)

    def delete_delivery(
        self, delivery_id: int, force_delete: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete a delivery. Local only.

        Cross-entity side effects (releasing inventory, refunding a
        payment) are the workflow's job. Callers that need them must
        go through DeliveryWorkflow.delete_delivery.

        Items attached to this delivery are unlinked first so the FK
        doesn't block the delete. The items themselves are not
        deleted — they belong to the order, not the delivery.
        """
        logger.info(
            "Deleting delivery with ID: %s (force=%s)",
            delivery_id, force_delete,
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

        # Unlink items first. Uses the same unlink helper as rollback.
        try:
            items = (
                self.order_item_repo.get_by_delivery(delivery_id)
                if hasattr(self.order_item_repo, "get_by_delivery")
                else []
            )
            self._unlink_items([
                getattr(i, "id_ordered_item", 0)
                for i in items
                if getattr(i, "id_ordered_item", 0)
            ])
        except Exception:
            logger.exception(
                "Failed to unlink items from delivery %s before delete",
                delivery_id,
            )

        success = self.delivery_repo.delete(existing)
        if not success:
            raise DeliveryDeleteFailedException(
                delivery_id=delivery_id,
                error="Repository returned False",
            )

        logger.info("Delivery %s deleted successfully", delivery_id)
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
            "Bulk deleting deliveries - provider:%s, order:%s, "
            "status:%s, force:%s",
            provider_id, order_id, status, force_delete,
        )
        try:
            status_lower = status.lower() if status else None
            deleted_count = self.delivery_repo.bulk_delete_by_criteria(
                provider_id, order_id, status_lower, force_delete,
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
            logger.error("Failed to bulk delete deliveries: %s", e)
            raise DeliveryBulkDeleteFailedException(
                provider_id=provider_id if provider_id > 0 else None,
                order_id=order_id if order_id > 0 else None,
                status=status,
                details={"error": str(e), "force_delete": force_delete},
            )

    def update_status_local(
        self, delivery_id: int, new_status: str,
    ) -> Delivery:
        """
        Local status write used by the workflow after the policy has
        approved the transition. No policy check here.
        """
        delivery = self.get_delivery_by_id(delivery_id)
        delivery.delivery_status = new_status.lower()
        return self.delivery_repo.update(delivery)

    def bulk_update_status_local(
        self, delivery_ids: List[int], new_status: str,
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