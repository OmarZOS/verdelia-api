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

Item linkage
------------
An `OrderedItem` with a non-null `delivery_id` is on that delivery;
one without is unassigned. `create_delivery` and `attach_ordered_items`
are the two ways that FK gets set. The `_advance_order_to_delivered`
side effect reads it to decide whether the order is truly complete —
delivery status alone is not enough, because a delivery can be
`delivered` while its items are still in `processing` (partial
handoff).
"""

from typing import List, Dict, Any, Optional
import logging

from anyio import from_thread

from repositories.financial_repository import FinancialRepository
from core.models.api_models import Delivery_API, DeliveryStatus, OrderedItem_API
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

# API field name → `Delivery` column name. Only the fields that differ.
# Any field not listed here is applied verbatim.
_API_TO_COLUMN = {
    "delivery_special_instructions": "special_instructions",
    "delivery_address_id": "address_id",
    "delivery_current_address_id": "current_address_id",
    "recipient_person": "recipient_person_id",
    "recipient_provider": "recipient_provider_id",
}


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
        # own repos (`delivery_repo`, `address_repo`,
        # `order_item_repo`).
        self.financial_repo = FinancialRepository()

    # ================================================================
    # CREATE
    # ================================================================

    def create_delivery(self, delivery_data: Delivery_API) -> Delivery:
        """
        Persist a new delivery.

        If `delivery_data.delivery_ordered_items` is populated, the
        service links those items (`OrderedItem.delivery_id = id`)
        after the delivery row is created. Items must already exist
        — they're the rows created by the order or cart workflow.
        """
        logger.info(
            "Creating delivery for source %s %s (%d items)",
            delivery_data.delivery_source_type,
            delivery_data.delivery_source_id,
            len(delivery_data.delivery_ordered_items or []),
        )
        return self.service.create_delivery(delivery_data)

    def attach_ordered_items(
        self,
        delivery_id: int,
        items: List[OrderedItem_API],
    ) -> Dict[str, Any]:
        """
        Assign existing `OrderedItem` rows to a delivery.

        The "select items and pass them to the delivery" path. Callers
        who created items first can attach them here without recreating
        the delivery.

        Item ids must be present. Items without an id are reported as
        `skipped`, not raised — they haven't been persisted.

        Refuses on terminal deliveries: a delivered/cancelled/returned
        delivery's item set is history.

        Returns:
            {delivery_id, attached, skipped, failed, overall_success}
        """
        delivery = self.service.get_delivery_by_id(delivery_id)
        current = (delivery.delivery_status or "").lower()
        if current in _TERMINAL_STATUSES:
            raise DeliveryNotEditableException(
                delivery_id=delivery_id,
                current_status=current,
            )

        attached: List[int] = []
        skipped: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []

        for api_item in items:
            item_id = getattr(api_item, "id_ordered_item", 0) or 0
            if item_id <= 0:
                skipped.append({
                    "reason": "no id",
                    "item": (
                        api_item.model_dump()
                        if hasattr(api_item, "model_dump")
                        else repr(api_item)
                    ),
                })
                continue
            try:
                self.service._link_items_to_delivery(delivery_id, [api_item])
                attached.append(item_id)
            except Exception as e:
                logger.exception(
                    "Failed to attach item %s to delivery %s",
                    item_id, delivery_id,
                )
                failed.append({"item_id": item_id, "error": str(e)})

        return {
            "delivery_id": delivery_id,
            "attached": attached,
            "skipped": skipped,
            "failed": failed,
            "overall_success": len(failed) == 0,
        }

    # ================================================================
    # INTERNAL: patch an in-memory instance
    # ================================================================
    #
    # No I/O. Takes an already-loaded Delivery and applies the fields
    # from the body. `_API_TO_COLUMN` maps the few API names that
    # differ from column names; everything else passes through.

    @staticmethod
    def _apply_body_to_instance(
        delivery: Delivery, body: Optional[Delivery_API],
    ) -> List[str]:
        if body is None:
            return []
        excluded = set(READ_ONLY_FIELDS)
        patch = body.model_dump(exclude_unset=True, exclude=excluded)
        if not patch:
            return []
        for field, value in patch.items():
            if hasattr(value, "value"):
                value = value.value
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
        """
        Advance the parent order to `DELIVERED` when every delivery
        for that order is delivered **and** every item attached to
        those deliveries is in a terminal-delivered state.

        Two checks are needed because delivery status and item status
        are independent:

          * A delivery can be `delivered` while one of its items is
            still `processing` — e.g. a partial handoff where the
            courier marked the shipment delivered but only handed
            over part of the box set.
          * An item can be `delivered` while the delivery row is
            still `out_for_delivery` — if the item is updated before
            the delivery transition. That would only happen via an
            external update, but the check is cheap.

        If item-level state is unavailable (older rows with no
        `delivery_id`), the check falls back to delivery status alone
        — a compatibility path that stops mattering once every
        item has a delivery id.
        """
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
        if not siblings:
            return

        # Check 1: every delivery for this order is delivered.
        all_deliveries_delivered = all(
            (d.delivery_status or "").lower() == "delivered"
            for d in siblings
        )
        if not all_deliveries_delivered:
            logger.info(
                "Order %s: not all deliveries delivered yet", order_id,
            )
            return

        # Check 2: every item attached to those deliveries is in a
        # terminal-delivered state. Items with no `delivery_id` are
        # ignored (they're either legacy or not yet assigned).
        item_repo = getattr(self.service, "order_item_repo", None)
        if item_repo is not None and hasattr(item_repo, "get_by_delivery"):
            for d in siblings:
                items = item_repo.get_by_delivery(d.id_delivery)
                for item in items or []:
                    status = (item.delivery_status or "").lower()
                    if status not in {"delivered", "returned", "cancelled"}:
                        logger.info(
                            "Order %s: item %s on delivery %s still "
                            "in status %r",
                            order_id,
                            getattr(item, "id_ordered_item", "?"),
                            d.id_delivery,
                            status,
                        )
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
            # `_safe_release_inventory` lives on the order workflow
            # and is async. The delivery workflow runs on a thread
            # with no event loop, so `from_thread.run` bridges to
            # the main loop.
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

    def _notify_recipient(self, delivery: Delivery) -> None:
        logger.debug("Delivery %s: notify recipient", delivery.id_delivery)

    # ── Provider / dispatch ─────────────────────────────────────────

    def _prepare_dispatch(self, delivery: Delivery) -> None:
        logger.debug("Delivery %s: prepare dispatch", delivery.id_delivery)

    def _assign_provider(self, delivery: Delivery) -> None:
        logger.debug(
            "Delivery %s: assign provider %s",
            delivery.id_delivery, delivery.delivery_provider_id,
        )

    # ── Refund recording ────────────────────────────────────────────

    def record_refund(
        self, delivery_id: int, amount, reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a completed refund payment against the delivery's linked
        invoice. Enables `delivered → refunded`.

        The only evidence the workflow *writes* — everything else is
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
        self, delivery_id: int, body: Delivery_API,
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
        self, delivery_id: int, current_address_id: int,
    ) -> Delivery:
        """
        Tracking-only update. Single read, single write. The status is
        not touched.

        Writes the *column* name (`current_address_id`), not the API
        field name (`delivery_current_address_id`).
        """
        self.service.validate_address_exists(current_address_id)

        delivery = self.service.get_delivery_by_id(delivery_id)
        delivery.current_address_id = current_address_id
        return self.service.persist_delivery(delivery)

    def update_address(
        self, delivery_id: int, address_id: int,
    ) -> Delivery:
        """
        Destination address update. Single read, single write. The
        status is not touched.

        Writes the *column* name (`address_id`), not the API field
        name (`delivery_address_id`).
        """
        self.service.validate_address_exists(address_id)

        delivery = self.service.get_delivery_by_id(delivery_id)
        delivery.address_id = address_id
        return self.service.persist_delivery(delivery)

    # ================================================================
    # DELETE / ARCHIVE
    # ================================================================

    def delete_delivery(
        self, delivery_id: int, force_delete: bool = False,
    ) -> Dict[str, Any]:
        """
        Load the delivery, release order-side inventory if it's tied
        to a placed order, then remove the row.

        `force_delete=False` is "archive" mode: requires terminal
        status. `force_delete=True` removes the row regardless.

        The release runs *before* the row is deleted and its failure
        propagates: a row that disappears while its reservation stays
        on a product is worse than a row that refuses to delete.
        """
        logger.info(
            "Deleting delivery %s (force=%s)", delivery_id, force_delete,
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
            # Propagate: if the reservation can't be released, the
            # row stays. Better a stuck delete than a phantom
            # reservation.
            self._release_inventory_for_delivery(delivery)

        return self.service.delete_delivery(
            delivery_id, force_delete=force_delete,
        )

    # ================================================================
    # READ HELPERS
    # ================================================================

    def get_delivery(
        self, delivery_id: int, *, eager: bool = True,
    ) -> Delivery:
        return self.service.get_delivery_by_id(
            delivery_id, eager_load=eager,
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
            delivery_id, eager_load=False,
        )
        current = (delivery.delivery_status or "").lower()
        return {
            "delivery_id": delivery_id,
            "current_status": current,
            "next_states": sorted(self.policy.allowed_targets(current)),
        }