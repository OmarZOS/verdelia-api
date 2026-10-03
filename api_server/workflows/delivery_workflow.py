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
"""

from typing import List, Dict, Any, Optional
import logging

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



# Signal fields on Delivery_API. Single source of truth for the patch filter.
SIGNAL_FIELDS = (
    "delivery_confirmed",
    "in_transit_acknowledged",
    "proof_captured",
    "failure_reported",
    "return_confirmed",
    "refund_completed",
)

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

# Terminal statuses. A delivery in one of these can be archived.
_TERMINAL_STATUSES = frozenset(
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

    # ================================================================
    # CREATE
    # ================================================================

    def create_delivery(self, delivery_data: Delivery_API) -> Delivery:
        """Persist a new delivery. No policy gate on the initial state."""
        logger.info(
            f"Creating delivery for source "
            f"{delivery_data.delivery_source_type} "
            f"{delivery_data.delivery_source_id}"
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
        """
        Mutate `delivery` with the patch fields from `body`. Returns
        the list of fields that changed (for logging).
        """
        if body is None:
            return []

        excluded = set(SIGNAL_FIELDS) | set(READ_ONLY_FIELDS)
        patch = body.model_dump(exclude_none=True, exclude=excluded)
        if not patch:
            return []

        for field, value in patch.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(delivery, field, value)

        return list(patch.keys())

    # ================================================================
    # TRANSITION (single read, single write, patch+transition in one pass)
    # ================================================================

    def transition(
        self,
        delivery_id: int,
        target: str,
        body: Optional[Delivery_API] = None,
        **signals: Any,
    ) -> Dict[str, Any]:
        """
        Patch (optionally) then transition, against one in-memory row.

        The row is read once, patched in memory, handed to the policy,
        and — if the decision allows — persisted. A denied transition
        leaves the row untouched: the patch is not written, because the
        operation is atomic from the caller's point of view.

        Signals (delivery_confirmed, proof_captured, …) come from the
        caller. They flow into the policy predicate, never into the
        persisted row.
        """
        delivery = self.service.get_delivery_by_id(delivery_id)
        
        if body.id_delivery > 0:
            patched_fields = self._apply_body_to_instance(delivery, body)


        decision = self.policy.decide_for_delivery(
            delivery, target=target, **signals
        )
        if not decision.allowed:
            logger.warning(
                f"Delivery {delivery_id} → '{target}' denied: "
                f"{decision.reason}"
            )
            raise DeliveryUpdateFailedException(
                delivery_id=delivery_id,
                error=f"Transition denied: {decision.reason}",
            )

        delivery.delivery_status = decision.target
        saved = self.service.persist_delivery(delivery)

        if body:
            logger.info(
                f"Delivery {delivery_id}"
                f"and transitioned to '{decision.target}'"
            )
        else:
            logger.info(
                f"Delivery {delivery_id}: transitioned to "
                f"'{decision.target}'"
            )

        self._dispatch_side_effects(
            delivery_id=delivery_id,
            side_effects=list(decision.side_effects),
            delivery=saved,
            **signals,
        )

        return {
            "delivery_id": delivery_id,
            "previous_status": decision.current,
            "new_status": decision.target,
            # "patched_fields": patched_fields,
            "side_effects": list(decision.side_effects),
        }

    # ================================================================
    # SIDE EFFECTS
    # ================================================================

    def _dispatch_side_effects(
        self,
        delivery_id: int,
        side_effects: List[str],
        delivery: Delivery,
        **signals: Any,
    ) -> None:
        for effect in side_effects:
            try:
                handler = {
                    "advance_order_to_shipped":
                        self._advance_order_to_shipped,
                    "advance_order_to_delivered":
                        self._advance_order_to_delivered,
                    "confirm_inventory":
                        self._confirm_inventory_for_delivery,
                    "release_inventory":
                        self._release_inventory_for_delivery,
                    "notify_recipient":
                        self._notify_recipient,
                    "prepare_dispatch":
                        self._prepare_dispatch,
                    "assign_provider":
                        self._assign_provider,
                }.get(effect)

                if handler is None:
                    logger.debug(
                        f"Delivery {delivery_id}: no handler for "
                        f"side effect '{effect}'"
                    )
                    continue

                handler(delivery, **signals)

            except Exception as e:
                logger.error(
                    f"Delivery {delivery_id}: side effect '{effect}' "
                    f"failed: {e}"
                )

    # ── Order advancement ───────────────────────────────────────────

    def _advance_order_to_shipped(self, delivery: Delivery, **_) -> None:
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
            logger.info(f"Order {order_id} advanced to SHIPPED")
        except Exception as e:
            logger.info(f"Order {order_id} not advanced to SHIPPED: {e}")

    def _advance_order_to_delivered(self, delivery: Delivery, **_) -> None:
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
            logger.info(
                f"Order {order_id}: sibling deliveries not all delivered"
            )
            return

        try:
            self.order_workflow.mark_order_delivered(
                order_id, delivery_delivered=True
            )
            logger.info(f"Order {order_id} advanced to DELIVERED")
        except Exception as e:
            logger.info(f"Order {order_id} not advanced to DELIVERED: {e}")

    # ── Inventory ───────────────────────────────────────────────────

    def _confirm_inventory_for_delivery(
        self, delivery: Delivery, **_
    ) -> None:
        if self.order_workflow is None:
            return
        if delivery.delivery_source_type != "placed_order":
            return
        order_id = delivery.delivery_source_id
        if not order_id:
            return
        try:
            result = self.order_workflow.confirm_inventory_for_order(
                order_id
            )
            logger.info(
                f"Order {order_id} inventory confirmed: "
                f"{result.get('items_confirmed', 0)} items"
            )
        except Exception as e:
            logger.error(
                f"Order {order_id} inventory confirmation failed: {e}"
            )

    def _release_inventory_for_delivery(
        self, delivery: Delivery, **_
    ) -> None:
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
            if items:
                import asyncio
                asyncio.get_event_loop().create_task(
                    self.order_workflow._safe_release_inventory(items)
                )
        except Exception as e:
            logger.error(
                f"Delivery {delivery.id_delivery}: inventory release "
                f"on behalf of order {order_id} failed: {e}"
            )

    # ── Notifications ───────────────────────────────────────────────

    def _notify_recipient(
        self, delivery: Delivery, **signals: Any
    ) -> None:
        logger.debug(
            f"Delivery {delivery.id_delivery}: notify recipient "
            f"(signals={signals})"
        )

    # ── Provider / dispatch ─────────────────────────────────────────

    def _prepare_dispatch(self, delivery: Delivery, **_) -> None:
        logger.debug(
            f"Delivery {delivery.id_delivery}: prepare dispatch"
        )

    def _assign_provider(self, delivery: Delivery, **_) -> None:
        logger.debug(
            f"Delivery {delivery.id_delivery}: assign provider "
            f"{delivery.delivery_provider_id}"
        )

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

        logger.info(f"Delivery {delivery_id}: patched {patched}")
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
        """
        logger.info(
            f"Deleting delivery {delivery_id} "
            f"(force={force_delete})"
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
            try:
                self._release_inventory_for_delivery(delivery)
            except Exception as e:
                logger.error(
                    f"Delivery {delivery_id}: inventory release on "
                    f"delete failed: {e}"
                )

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