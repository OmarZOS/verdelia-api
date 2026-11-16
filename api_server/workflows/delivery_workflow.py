# workflows/delivery_workflow.py
"""
Delivery workflow — orchestration layer.

Owns every read, every write, and every policy decision that touches
a delivery. The router stays thin: it validates request shape, calls
one workflow method, and translates domain exceptions to HTTP.

Session contract
----------------
Each public method performs at most one read of the delivery row and
at most one write. A request that both patches metadata and transitions
status does both against the same in-memory instance so the ORM
session sees one coherent object — no second fetch, no detached
stale copy.

Side-effect ordering
--------------------
`transition()` runs *before* the status change for any effect that
must be able to abort the transition. Today that's `release_inventory`:
if the reservation can't be released, the delivery must not move to
`cancelled`, otherwise the reservation is orphaned. All other effects
run *after* the persist, and their failures are logged but do not
abort the transition.
"""

from typing import List, Dict, Any, Optional
import logging

from anyio import from_thread

from repositories.financial_repository import FinancialRepository
from core.models.api_models import Delivery_API, DeliveryStatus
from core.models.models import Delivery
from core.exceptions.specific.delivery_exceptions import (
    DeliveryNotFoundException,
    DeliveryNotEditableException,
    DeliveryNotArchivableException,
    DeliveryUpdateFailedException,
)

from policies.delivery_policy import DeliveryPolicy
from services.delivery_service import DeliveryService

from core.logging_config import get_logger

logger = get_logger(__name__)




READ_ONLY_FIELDS = (
    "id_delivery",
    "delivery_created_at",
    "delivery_updated_at",
    "delivery_status",
    "delivery_ordered_items",
)

_NON_EDITABLE_STATUSES = frozenset(
    {"delivered", "cancelled", "returned", "refunded"}
)
_TERMINAL_STATUSES = frozenset(
    {"delivered", "cancelled", "returned", "refunded"}
)


# Signal fields on Delivery_API. Single source of truth for the patch filter.
SIGNAL_FIELDS = (
    "delivery_confirmed",
    "in_transit_acknowledged",
    "proof_captured",
    "failure_reported",
    "return_confirmed",
    "refund_completed",
)

_API_TO_COLUMN = {
    "delivery_special_instructions": "special_instructions",
    "delivery_address_id": "address_id",
    "delivery_current_address_id": "current_address_id",
}

# Read-only fields on Delivery_API: never patched, status only ever
# changes through a policy-approved transition.
READ_ONLY_FIELDS = (
    "id_delivery",
    "delivery_created_at",
    "delivery_updated_at",
    "delivery_status",
    "delivery_ordered_items",
)

# Statuses whose details are frozen. Once the delivery has reached one
# of these, the row is history and edits are refused.
_NON_EDITABLE_STATUSES = frozenset(
    {"delivered", "cancelled", "returned", "refunded"}
)



class DeliveryWorkflow:
    """Orchestration around DeliveryService."""

    def __init__(
        self,
        service: Optional[DeliveryService] = None,
        order_workflow: Optional[Any] = None,
        delivery_policy: Optional[DeliveryPolicy] = None,
    ):
        self.service = service or DeliveryService()
        self.order_workflow = order_workflow
        self.policy = delivery_policy or DeliveryPolicy()

        # The only repo the policy reads through (for refund
        # verification). Everything else goes through the service's
        # own repos (`delivery_repo`, `address_repo`).
        self.financial_repo = FinancialRepository()

    # ================================================================
    # CREATE
    # ================================================================

    def create_delivery(self, delivery_data: Delivery_API) -> Delivery:
        """Persist a new delivery. No policy gate on the initial state."""
        logger.info(
            "Creating delivery for source %s %s",
            delivery_data.delivery_source_type,
            delivery_data.delivery_source_id,
        )
        return self.service.create_delivery(delivery_data)

    # ================================================================
    # INTERNAL: patch an in-memory instance
    # ================================================================
    #
    # No I/O. Takes an already-loaded Delivery and applies the fields
    # from the body. This is the only thing the public methods share,
    # and it must not read the row again.

    @staticmethod
    def _apply_body_to_instance(
        delivery: Delivery, body: Optional[Delivery_API]
    ) -> List[str]:
        if body is None:
            return []
        excluded = set(READ_ONLY_FIELDS)
        # `exclude_unset=True` is what we want: only fields the caller
        # actually provided end up in the patch. `exclude_none=True`
        # only skips fields whose *value* is None, which still includes
        # every field with a non-None default (0, "", 0.0, "standard",
        # etc.) — those then overwrite whatever the caller had set on a
        # previous request.
        patch = body.model_dump(exclude_unset=True, exclude=excluded)
        if not patch:
            return []
        for field, value in patch.items():
            if hasattr(value, "value"):
                value = value.value
            # Map API field names to column names where they differ.
            column = _API_TO_COLUMN.get(field, field)
            setattr(delivery, column, value)
        return list(patch.keys())


    # ================================================================
    # TRANSITION (single read, single write, patch+transition in one pass)
    # ================================================================

    def transition(
        self,
        delivery_id: int,
        target: str,
        body: Optional[Delivery_API] = None,
    ) -> Dict[str, Any]:
        delivery = self.service.get_delivery_by_id(delivery_id)

        patched_fields: List[str] = []
        if body is not None:
            patched_fields = self._apply_body_to_instance(delivery, body)

        decision = self.policy.decide_for_delivery(
            delivery, target=target, wf=self,
        )
        if not decision.allowed:
            logger.warning(
                "Delivery %s → '%s' denied. State: "
                "status=%r recipient_person_id=%r recipient_provider_id=%r "
                "address_id=%r current_address_id=%r "
                "package_count=%r total_weight=%r shipping_method=%r "
                "carrier=%r broker=%r provider=%r",
                delivery_id, target,
                getattr(delivery, "delivery_status", None),
                getattr(delivery, "recipient_person_id", None),
                getattr(delivery, "recipient_provider_id", None),
                getattr(delivery, "address_id", None),
                getattr(delivery, "current_address_id", None),
                getattr(delivery, "delivery_package_count", None),
                getattr(delivery, "delivery_total_weight", None),
                getattr(delivery, "delivery_shipping_method", None),
                getattr(delivery, "carrying_user_id", None),
                getattr(delivery, "delivery_broker_id", None),
                getattr(delivery, "delivery_provider_id", None),
            )


            logger.warning(
                "Delivery %s → '%s' denied: %s",
                delivery_id, target, decision.reason,
            )
            raise DeliveryUpdateFailedException(
                delivery_id=delivery_id,
                error=f"Transition denied: {decision.reason}",
            )

        pre_persist = {"release_inventory"}
        for effect in decision.side_effects:
            if effect not in pre_persist:
                continue
            handler = self._effect_handler(effect)
            if handler is not None:
                handler(delivery)

        delivery.delivery_status = decision.target
        saved = self.service.persist_delivery(delivery)

        remaining = [e for e in decision.side_effects if e not in pre_persist]
        self._dispatch_side_effects(
            delivery_id=delivery_id,
            side_effects=remaining,
            delivery=saved,
        )

        return {
            "delivery_id": delivery_id,
            "previous_status": decision.current,
            "new_status": decision.target,
            "patched_fields": patched_fields,
            "side_effects": list(decision.side_effects),
        }

    # ================================================================
    # SIDE EFFECTS
    # ================================================================

    def _effect_handler(self, effect: str):
        return {
            "advance_order_to_shipped": self._advance_order_to_shipped,
            "advance_order_to_delivered": self._advance_order_to_delivered,
            "confirm_inventory": self._confirm_inventory_for_delivery,
            "release_inventory": self._release_inventory_for_delivery,
            "notify_recipient": self._notify_recipient,
            "prepare_dispatch": self._prepare_dispatch,
            "assign_provider": self._assign_provider,
        }.get(effect)

    def _dispatch_side_effects(
        self,
        delivery_id: int,
        side_effects: List[str],
        delivery: Delivery,
    ) -> None:
        for effect in side_effects:
            handler = self._effect_handler(effect)
            if handler is None:
                continue
            try:
                handler(delivery)
            except Exception:
                logger.exception(
                    "Delivery %s: side effect '%s' failed",
                    delivery_id, effect,
                )


    # ── Order advancement ───────────────────────────────────────────

    def _advance_order_to_shipped(self, delivery: Delivery) -> None:
        if self.order_workflow is None:
            return
        if delivery.delivery_source_type != "placed_order":
            return
        order_id = delivery.delivery_source_id
        if not order_id:
            return
        try:
            self.order_workflow.mark_order_shipped(
                order_id, delivery_confirmed=True
            )
            logger.info("Order %s advanced to SHIPPED", order_id)
        except Exception as e:
            logger.info("Order %s not advanced to SHIPPED: %s", order_id, e)


    def _advance_order_to_delivered(self, delivery: Delivery) -> None:
        if self.order_workflow is None:
            return
        if delivery.delivery_source_type != "placed_order":
            return
        order_id = delivery.delivery_source_id
        if not order_id:
            return
        siblings = self.service.delivery_repo.get_by_source(
            "placed_order", order_id
        )
        all_delivered = bool(siblings) and all(
            (d.delivery_status or "").lower() == "delivered"
            for d in siblings
        )
        if not all_delivered:
            return
        try:
            self.order_workflow.mark_order_delivered(
                order_id, delivery_delivered=True
            )
            logger.info("Order %s advanced to DELIVERED", order_id)
        except Exception as e:
            logger.info("Order %s not advanced to DELIVERED: %s", order_id, e)


    # ── Inventory ───────────────────────────────────────────────────

    def _confirm_inventory_for_delivery(self, delivery: Delivery) -> None:
        if self.order_workflow is None:
            return
        if delivery.delivery_source_type != "placed_order":
            return
        order_id = delivery.delivery_source_id
        if not order_id:
            return
        try:
            result = self.order_workflow.confirm_inventory_for_order(order_id)
            logger.info(
                "Order %s inventory confirmed: %s items",
                order_id, result.get("items_confirmed", 0),
            )
        except Exception:
            logger.exception(
                "Order %s inventory confirmation failed", order_id
            )


    def _release_inventory_for_delivery(self, delivery: Delivery) -> None:
        if self.order_workflow is None:
            return
        if delivery.delivery_source_type != "placed_order":
            return
        order_id = delivery.delivery_source_id
        if not order_id:
            return
        try:
            order = self.order_workflow.service.get_order_by_id(
                order_id, with_items=True
            )
            items = list(order.ordered_item or [])
            if not items:
                return
            from_thread.run(
                self.order_workflow._safe_release_inventory, items
            )
            logger.info(
                "Delivery %s: released inventory for order %s (%d items)",
                delivery.id_delivery, order_id, len(items),
            )
        except Exception:
            logger.exception(
                "Delivery %s: inventory release on behalf of order %s failed",
                delivery.id_delivery, order_id,
            )
            raise


    # ── Notifications ───────────────────────────────────────────────

    def _notify_recipient(
        self, delivery: Delivery, **signals: Any
    ) -> None:
        logger.debug(
            "Delivery %s: notify recipient (signals=%s)",
            delivery.id_delivery, signals,
        )

    # ── Provider / dispatch ─────────────────────────────────────────

    def _prepare_dispatch(self, delivery: Delivery, **_) -> None:
        logger.debug(
            "Delivery %s: prepare dispatch", delivery.id_delivery
        )

    def _assign_provider(self, delivery: Delivery, **_) -> None:
        logger.debug(
            "Delivery %s: assign provider %s",
            delivery.id_delivery, delivery.delivery_provider_id,
        )


    def record_refund(
        self, delivery_id: int, amount, reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a completed refund payment against the delivery's linked
        invoice. Enables `delivered → refunded`.

        This is the only evidence we *write* — everything else is
        verified from columns that already exist on the delivery.
        """
        delivery = self.service.get_delivery_by_id(delivery_id)
        if not delivery.delivery_invoice_ref:
            raise DeliveryUpdateFailedException(
                delivery_id=delivery_id,
                error="Delivery has no linked invoice to refund",
            )
        payment = self.financial_repo.create_refund_payment(
            invoice_id=delivery.delivery_invoice_ref,
            amount=amount,
            reference=reference,
        )
        logger.info(
            "Delivery %s: refund recorded against invoice %s (payment id=%s)",
            delivery_id, delivery.delivery_invoice_ref, payment.id_payment,
        )
        return {
            "id_payment": payment.id_payment,
            "delivery_id": delivery_id,
            "invoice_id": delivery.delivery_invoice_ref,
            "amount": str(amount),
        }


    # ================================================================
    # METADATA-ONLY WRITE
    # ================================================================

    def update_details(
        self, delivery_id: int, body: Delivery_API
    ) -> Delivery:
        """
        Metadata-only update. Refuses on terminal deliveries.

        Single read, single write. The row is loaded, the body fields
        are applied in memory, and the row is persisted once.
        """
        delivery = self.service.get_delivery_by_id(delivery_id)
        current = (delivery.delivery_status or "").lower()

        if current in _NON_EDITABLE_STATUSES:
            raise DeliveryNotEditableException(
                delivery_id=delivery_id,
                current_status=current,
            )

        patched = self._apply_body_to_instance(delivery, body)
        if not patched:
            return delivery

        logger.info("Delivery %s: patched %s", delivery_id, patched)
        return self.service.persist_delivery(delivery)

    # ================================================================
    # NON-STATUS WRITES
    # ================================================================

    def update_tracking(
        self, delivery_id: int, current_address_id: int
    ) -> Delivery:
        """
        Tracking-only update. Single read, single write. The status is
        not touched.
        """
        self.service.validate_address_exists(current_address_id)

        delivery = self.service.get_delivery_by_id(delivery_id)
        delivery.delivery_current_address_id = current_address_id
        return self.service.persist_delivery(delivery)

    def update_address(
        self, delivery_id: int, address_id: int
    ) -> Delivery:
        """
        Destination address update. Single read, single write. The
        status is not touched.
        """
        self.service.validate_address_exists(address_id)

        delivery = self.service.get_delivery_by_id(delivery_id)
        delivery.delivery_address_id = address_id
        return self.service.persist_delivery(delivery)

    # ================================================================
    # DELETE / ARCHIVE
    # ================================================================

    def delete_delivery(
        self, delivery_id: int, force_delete: bool = False
    ) -> Dict[str, Any]:
        """
        Load the delivery, release order-side inventory if it's tied to
        a placed order, then remove the row.

        `force_delete=False` is the "archive" mode: it requires the
        delivery to already be in a terminal state. `force_delete=True`
        removes the row regardless.

        The release runs *before* the row is deleted and its failure
        propagates: a row that disappears while its reservation stays
        on the product is worse than a row that refuses to delete.
        """
        logger.info(
            "Deleting delivery %s (force=%s)", delivery_id, force_delete
        )

        delivery = self.service.get_delivery_by_id(delivery_id)
        current = (delivery.delivery_status or "").lower()

        if not force_delete and current not in _TERMINAL_STATUSES:
            raise DeliveryNotArchivableException(
                delivery_id=delivery_id,
                current_status=current,
            )

        if (
            delivery.delivery_source_type == "placed_order"
            and delivery.delivery_source_id
            and self.order_workflow is not None
        ):
            # Propagate: if the reservation can't be released, the row
            # stays. Better a stuck delete than a phantom reservation.
            self._release_inventory_for_delivery(delivery)

        return self.service.delete_delivery(
            delivery_id, force_delete=force_delete
        )

    # ================================================================
    # READ HELPERS
    # ================================================================

    def get_delivery(
        self, delivery_id: int, *, eager: bool = True
    ) -> Delivery:
        return self.service.get_delivery_by_id(
            delivery_id, eager_load=eager
        )

    def list_deliveries(
        self,
        *,
        provider_id: int = 0,
        source_type: Optional[str] = None,
        source_id: int = 0,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Delivery]:
        return self.service.get_all_deliveries(
            provider_id=provider_id,
            order_id=source_id if source_type == "placed_order" else 0,
            broker_id=0,
            offset=offset,
            limit=limit,
        )

    def next_states(self, delivery_id: int) -> Dict[str, Any]:
        delivery = self.service.get_delivery_by_id(
            delivery_id, eager_load=False
        )
        current = (delivery.delivery_status or "").lower()
        return {
            "delivery_id": delivery_id,
            "current_status": current,
            "next_states": sorted(self.policy.allowed_targets(current)),
        }