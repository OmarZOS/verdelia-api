# services/order_workflow.py
"""
Order workflow — orchestration layer.

Owns every call that crosses a process boundary:
  - InventoryServiceClient (availability, reserve, confirm, release)
  - FinanceServiceClient    (create payment, confirm payment)

Owns the sequencing of the three phases:
  Phase 1  create_order
  Phase 2  process_payment
  Phase 3  confirm_inventory_for_order
  Finalize finalize_order  → Phase 2 + Phase 3

Owns remote failure handling: when a remote call fails after local
persistence, the workflow asks the service to roll back local entities and
asks the inventory client to release reservations.

Owns state transitions via policies:
  - PlacedOrderPolicy    decides PENDING → PROCESSING after payment
  - PaymentPolicy        (used by the finance side; not called here today)
  - InvoicePolicy        decides unpaid → paid after payment confirm
  - OrderedItemPolicy    (used by the delivery flow; not called here today)

Every transition is decided by a policy *before* the ORM row is mutated.
The policies are pure; the workflow persists what they approve.
"""

from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from core.exceptions.specific.finance_exceptions import PaymentNotConfirmedException
from policies.placed_order_policy import PlacedOrderPolicy
from storage.wrappers.finance_client import FinanceServiceClient
from storage.wrappers.inventory_client import InventoryServiceClient
from core.models.api_models import Delivery_Info_API, OrderedItem_API, PlacedOrder_API
from core.models.models import PlacedOrder, OrderedItem, Invoice, Delivery
from core.exceptions.specific.product_exceptions import (
    ProductQuantityNotEnoughException,
)
from policies import (
    
    InvoicePolicy,
    OrderedItemPolicy,
    PaymentPolicy,
)
from services.order_service import OrderService

from core.logging_config import get_logger

logger = get_logger(__name__)



class OrderWorkflow:
    """
    Orchestration around OrderService.

    The workflow never touches repositories directly, and the service never
    touches remote clients. Every cross-boundary call goes through this
    class. Every state change is gated by a policy decision before it is
    persisted.
    """

    def __init__(
        self,
        service: Optional[OrderService] = None,
        inventory_client: Optional[InventoryServiceClient] = None,
        finance_client: Optional[FinanceServiceClient] = None,
        order_policy: Optional[PlacedOrderPolicy] = None,
        invoice_policy: Optional[InvoicePolicy] = None,
        item_policy: Optional[OrderedItemPolicy] = None,
        payment_policy: Optional[PaymentPolicy] = None,
    ):
        self.service = service or OrderService()
        self.inventory_client = inventory_client or InventoryServiceClient()
        self.finance_client = finance_client or FinanceServiceClient()

        self.order_policy = order_policy or PlacedOrderPolicy()
        self.invoice_policy = invoice_policy or InvoicePolicy()
        self.item_policy = item_policy or OrderedItemPolicy()
        self.payment_policy = payment_policy or PaymentPolicy()

    # ================================================================
    # PHASE 1 — CREATE ORDER
    # ================================================================




    async def create_order(
        self,
        items: List[OrderedItem_API],
        order_data: PlacedOrder_API,
        payment_method: str = 'card',
        user_id: Optional[int] = None,
        delivery_data: Optional[Delivery_Info_API] = None,
    ) -> Tuple[List[int], PlacedOrder, Dict[str, Any]]:
        logger.info(
            f"Creating new order for user: {order_data.ordering_user_id}"
        )

        ordering_user = self.service.user_repo.get_by_id(
            order_data.ordering_user_id
        )
        if not ordering_user:
            from core.exceptions.handler import UserNotFoundException
            raise UserNotFoundException(user_id=order_data.ordering_user_id)

        if not user_id:
            user_id = order_data.ordering_user_id

        created_order: Optional[PlacedOrder] = None
        created_invoice: Optional[Invoice] = None
        created_items: List[OrderedItem] = []
        created_deliveries: List[Delivery] = []

        # Track exactly which items were reserved remotely, not just
        # whether the reserve call "succeeded". A partial reserve can
        # leave some items reserved even when the call raises.
        reserved_item_ids: List[int] = []

        try:
            # Step 1 — remote read-only availability check
            logger.info("Step 1: Checking inventory availability...")
            await self._check_inventory_availability(items)

            # Step 2 — local persist
            logger.info("Step 2: Persisting order entities...")
            (
                created_order,
                created_items,
                created_invoice,
                created_deliveries,
            ) = self.service.persist_order_entities(
                items=items,
                order_data=order_data,
                user_id=user_id,
                delivery_data=delivery_data,
            )

            # Step 3 — remote reservation
            logger.info("Step 3: Reserving inventory...")
            reserved_item_ids = await self._reserve_inventory(created_items)
            logger.info("✅ Inventory reserved successfully")

            result = {
                'order_id': created_order.id_placed_order,
                'invoice_id': created_invoice.invoice_id,
                'payment_id': None,
                'payment_status': None,
                'inventory_reserved': True,
                'inventory_deducted': False,
            }
            logger.info(
                f"✅ Order {created_order.id_placed_order} created "
                f"(payment and inventory confirmation are pending)"
            )
            return (
                [p.ordered_quantity for p in created_items],
                created_order,
                result,
            )

        except Exception as e:
            logger.error(f"Order creation failed: {e}")

            # Local rollback FIRST: if it fails, we still have the
            # list of reserved_item_ids and can decide whether to
            # release. If we released first and the local rollback
            # then failed, we'd have orphaned DB rows pointing at
            # inventory that no longer belongs to them.
            try:
                self.service.rollback_entities(
                    order=created_order,
                    invoice=created_invoice,
                    items=created_items,
                    deliveries=created_deliveries,
                )
                local_rollback_ok = True
            except Exception:
                logger.exception(
                    "Order rollback failed — entities may be dirty for "
                    "order %s",
                    created_order.id_placed_order if created_order else None,
                )
                local_rollback_ok = False

            # Remote: release exactly what we know we reserved.
            # If local rollback failed, still release — leaked remote
            # reservations are worse than an orphaned local row.
            if reserved_item_ids:
                await self._safe_release_inventory_by_ids(reserved_item_ids)

            if not local_rollback_ok:
                raise
            raise

    # ================================================================
    # PHASE 2 — PROCESS PAYMENT
    # ================================================================

    async def process_payment(
        self,
        order_id: int,
        payment_method: str = 'card',
        transaction_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info("Processing payment for order %s...", order_id)

        # ── Local reads ──────────────────────────────────────────────
        order = self.service.get_order_by_id(order_id, with_items=True)
        invoice = self.service.get_invoice_for_order(order)

        # ── Guard 1: invoice already paid ────────────────────────────
        if self.invoice_policy.normalize(invoice.invoice_status) == "paid":
            logger.info("Order %s invoice already paid — skipping", order_id)
            return {
                "order_id": order_id,
                "invoice_id": invoice.invoice_id,
                "payment_id": None,
                "payment_status": "paid",
            }

        # ── Guard 2: existing completed payment for this invoice ─────
        # Without this, a retry after a "money moved but invoice not
        # marked paid" failure would create a second payment.
        existing = self.service.get_completed_payment_for_invoice(
            invoice.invoice_id
        )
        if existing:
            logger.info(
                "Invoice %s already has completed payment %s — skipping",
                invoice.invoice_id, existing.payment_id,
            )
            return {
                "order_id": order_id,
                "invoice_id": invoice.invoice_id,
                "payment_id": existing.payment_id,
                "payment_status": existing.payment_status,
            }

        # ── Pre-flight: STRUCTURAL ONLY ──────────────────────────────
        #
        # The invoice and order predicates require facts we don't have
        # yet:
        #   - invoice: `unpaid_to_paid` requires a captured_amount. The
        #     payment hasn't happened, so there is no amount to pass.
        #   - order: `payment_confirmed` requires payment_paid=True. Same.
        #
        # Calling the predicates with `None` / `False` rejects every
        # invoice, which is exactly what produced the 500s. Since the
        # policy classes are fixed, do the structural checks inline here.
        # The predicates run unchanged at commit time, below, once real
        # values exist.
        self._assert_invoice_can_reach_paid(invoice)
        self._assert_order_can_reach_processing(order)
        # Reject zero/negative invoice totals BEFORE touching finance.
        # A payment record for 0.00 should never exist.
        self._assert_invoice_has_payable_total(invoice)

        # ── Remote: create payment ───────────────────────────────────
        payment_payload = self.service.build_payment_create_payload(
            order=order, invoice=invoice, payment_method=payment_method,
        )

        # Defense in depth: reject a non-positive payload amount before
        # it reaches finance. The pre-flight above already checked the
        # invoice total, but the payload is what finance actually sees.
        payload_amount = self._as_decimal(
            payment_payload.get("amount")
            if isinstance(payment_payload, dict)
            else getattr(payment_payload, "amount", None)
        )
        if payload_amount is None or payload_amount <= 0:
            raise ValueError(
                f"Refusing to create payment for order {order_id}: "
                f"payload amount {payload_amount!r} is not positive"
            )

        created = await self.finance_client.create_payment(payment_payload)
        logger.info(
            "Payment %s created (status=%s)", created.id, created.status
        )

        # ── Remote: confirm payment ──────────────────────────────────
        details = (
            transaction_details
            or self.service.build_payment_transaction_details(
                order=order, invoice=invoice, payment_method=payment_method,
            )
        )
        confirmed = await self.finance_client.confirm_payment(
            payment_id=created.id,
            transaction_details=details,
        )
        logger.info(
            "Payment %s confirm returned status=%s",
            confirmed.id, confirmed.status,
        )

        # ── Sanity: confirm must not return a different payment ──────
        if confirmed.id != created.id:
            raise ValueError(
                f"create/confirm returned different payment ids: "
                f"{created.id} vs {confirmed.id}"
            )

        # ── Sanity: confirm must have actually completed ─────────────
        confirmed_status = self._normalize_payment_status(confirmed.status)
        if confirmed_status not in ("completed", "confirmed", "paid"):
            raise PaymentNotConfirmedException(
                payment_id=confirmed.id,
                status=confirmed.status,
                invoice_id=invoice.invoice_id,
            )

        # ── Sanity: confirmed amount must be positive ────────────────
        #
        # A payment the finance service reports as completed but with
        # amount <= 0 is a finance-side integrity failure, not a
        # "not confirmed" failure. Raise it distinctly so the
        # reconciliation log identifies the real problem.
        captured = self._as_decimal(confirmed.amount)
        if captured is None or captured <= 0:
            logger.error(
                "ZERO-AMOUNT CONFIRMED PAYMENT: order=%s invoice=%s "
                "payment=%s status=%s amount=%r — finance confirmed a "
                "non-positive payment; manual reconciliation required",
                order_id, invoice.invoice_id, confirmed.id,
                confirmed.status, confirmed.amount,
            )
            raise ValueError(
                f"Finance confirmed payment {confirmed.id} with "
                f"non-positive amount {confirmed.amount!r} for invoice "
                f"{invoice.invoice_id}"
            )

        # ── Commit: does the captured amount clear the invoice? ──────
        #
        # This is the real gate on unpaid → paid. The pre-flight only
        # checked that the edge exists; here the predicate runs with the
        # actual captured amount and can reject under/over payment.
        invoice_commit = self.invoice_policy.decide_for_invoice(
            invoice,
            target="paid",
            captured_amount=float(captured),
        )
        if not invoice_commit.allowed:
            logger.error(
                "ORPHANED PAYMENT: order=%s invoice=%s payment=%s "
                "captured=%s reason=%s",
                order_id, invoice.invoice_id, confirmed.id,
                captured, invoice_commit.reason,
            )
            raise ValueError(
                f"Payment captured {captured} but invoice cannot be "
                f"marked paid: {invoice_commit.reason}"
            )

        # ── Commit: order must be able to reach PROCESSING ───────────
        #
        # Now that payment_paid=True is a real fact, run the order
        # predicate for real. If this rejects, the invoice transition
        # above is NOT persisted (persist happens below), so the
        # invoice stays unpaid and the money is orphaned — logged for
        # reconciliation.
        order_commit = self.order_policy.decide(
            current=self.order_policy.normalize(order.order_state),
            target="PROCESSING",
            input=order,
            payment_paid=True,
        )
        if not order_commit.allowed:
            logger.error(
                "ORPHANED PAYMENT: order=%s invoice=%s payment=%s "
                "captured=%s reason=%s",
                order_id, invoice.invoice_id, confirmed.id,
                captured, order_commit.reason,
            )
            raise ValueError(
                f"Payment captured but order cannot move to PROCESSING: "
                f"{order_commit.reason}"
            )

        # ── Persist ──────────────────────────────────────────────────
        self.service.mark_invoice_paid(invoice)
        self.service.advance_order_after_payment(order)

        logger.info(
            "Order %s: invoice %s → %s, order %s → %s",
            order_id,
            invoice_commit.current, invoice_commit.target,
            order_commit.current, order_commit.target,
        )
        return {
            "order_id": order.id_placed_order,
            "invoice_id": invoice.invoice_id,
            "payment_id": confirmed.id,
            "payment_status": confirmed.status,
        }

    # ================================================================
    # PHASE 3 — CONFIRM INVENTORY
    # ================================================================

    async def confirm_inventory_for_order(
        self, order_id: int
    ) -> Dict[str, Any]:
        """
        Phase 3 orchestration (by order id):
          1. local: load order items
          2. remote: confirm inventory
        Idempotent — the silo ignores already-confirmed items.

        The items' `delivery_status` is not changed here:
        confirmation of inventory is an inventory-side fact, not a
        delivery-side state change. The delivery flow drives the item
        state via OrderedItemPolicy when the goods actually move.
        """
        logger.info(f"Confirming inventory for order {order_id}...")

        order = self.service.get_order_by_id(order_id, with_items=True)
        items = list(order.ordered_item or [])
        if not items:
            logger.info(f"Order {order_id} has no items to confirm")
            return {
                'order_id': order_id,
                'items_confirmed': 0,
                'success': True,
            }

        return await self.confirm_inventory_for_items(
            items, order_id=order_id
        )

    async def confirm_inventory_for_items(
        self,
        ordered_items: List[Any],
        *,
        order_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Phase 3 orchestration (by items):
          1. local: normalize items
          2. remote: confirm inventory
        Accepts ORM objects or dicts. Used by the delivery flow when only a
        subset of items is being confirmed.
        """
        confirm_items = self.service.build_confirm_payload(ordered_items)

        if not confirm_items:
            label = f"order {order_id}" if order_id is not None else "items"
            logger.info(f"No items to confirm for {label}")
            return {
                'order_id': order_id,
                'items_confirmed': 0,
                'success': True,
            }

        confirm_response = await self.inventory_client.confirm_inventory(
            items=confirm_items,
            item_type='ordered_item',
        )

        if isinstance(confirm_response, dict):
            if not confirm_response.get('success', True):
                raise Exception(
                    f"Inventory confirmation failed: {confirm_response}"
                )

        label = f"order {order_id}" if order_id is not None else "items"
        logger.info(f"✅ Inventory confirmed for {label}")
        return {
            'order_id': order_id,
            'items_confirmed': len(confirm_items),
            'success': True,
        }

    # ================================================================
    # EXPLICIT STATE TRANSITIONS (policy-gated)
    # ================================================================

    async def mark_order_shipped(
        self,
        order_id: int,
        *,
        delivery_confirmed: bool = True,
    ) -> Dict[str, Any]:
        """
        PROCESSING → SHIPPED, gated by PlacedOrderPolicy.

        Called by the delivery flow once every delivery for the order has
        reached `shipped` or later. The workflow doesn't verify that
        condition itself — the caller does, and asserts it via
        `delivery_confirmed`.
        """
        order = self.service.get_order_by_id(order_id, with_items=True)

        decision = self.order_policy.decide_for_order(
            order,
            target='SHIPPED',
            delivery_confirmed=delivery_confirmed,
        )
        if not decision.allowed:
            raise ValueError(
                f"Order transition denied: {decision.reason}"
            )

        order.order_state = decision.target
        order.updated_at = datetime.now()
        self.service.order_repo.update_order(order)

        logger.info(
            f"Order {order_id}: {decision.current} → {decision.target} "
            f"(side effects: {decision.side_effects})"
        )
        return {
            'order_id': order_id,
            'previous_state': decision.current,
            'new_state': decision.target,
            'side_effects': decision.side_effects,
        }

    async def mark_order_delivered(
        self,
        order_id: int,
        *,
        delivery_delivered: bool = True,
    ) -> Dict[str, Any]:
        """SHIPPED → DELIVERED, gated by PlacedOrderPolicy."""
        order = self.service.get_order_by_id(order_id, with_items=True)

        decision = self.order_policy.decide_for_order(
            order,
            target='DELIVERED',
            delivery_delivered=delivery_delivered,
        )
        if not decision.allowed:
            raise ValueError(
                f"Order transition denied: {decision.reason}"
            )

        order.order_state = decision.target
        order.updated_at = datetime.now()
        self.service.order_repo.update_order(order)

        logger.info(
            f"Order {order_id}: {decision.current} → {decision.target}"
        )
        return {
            'order_id': order_id,
            'previous_state': decision.current,
            'new_state': decision.target,
            'side_effects': decision.side_effects,
        }

    async def cancel_order(
        self,
        order_id: int,
        *,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        * → CANCELLED, gated by PlacedOrderPolicy.

        Order of operations: persist first, release second. If the
        persist fails, nothing has been released and the order is
        still live. If the release fails, the order is cancelled but
        the reservation is leaked — we log a distinct error so it is
        reconcilable, rather than pretending the release succeeded.
        """
        order = self.service.get_order_by_id(order_id, with_items=True)

        decision = self.order_policy.decide_for_order(order, target='CANCELLED')
        if not decision.allowed:
            raise ValueError(
                f"Order transition denied: {decision.reason}"
            )

        # Persist first.
        order.order_state = decision.target
        order.updated_at = datetime.now()
        self.service.order_repo.update_order(order)

        # Then release — failure here does NOT un-cancel the order,
        # but is loudly logged for reconciliation.
        items = list(order.ordered_item or [])
        if items:
            try:
                await self._safe_release_inventory(items)
            except Exception:
                logger.error(
                    "Cancel succeeded but inventory release failed for "
                    "order %s — reservations are leaked and must be "
                    "reconciled",
                    order_id,
                )

        logger.info(
            f"Order {order_id}: {decision.current} → {decision.target} "
            f"(reason={reason})"
        )
        return {
            'order_id': order_id,
            'previous_state': decision.current,
            'new_state': decision.target,
            'reason': reason,
            'side_effects': decision.side_effects,
        }


    async def mark_order_idunded(
        self,
        order_id: int,
        *,
        refund_completed: bool = True,
    ) -> Dict[str, Any]:
        """DELIVERED → REFUNDED, gated by PlacedOrderPolicy."""
        order = self.service.get_order_by_id(order_id, with_items=True)

        decision = self.order_policy.decide_for_order(
            order,
            target='REFUNDED',
            refund_completed=refund_completed,
        )
        if not decision.allowed:
            raise ValueError(
                f"Order transition denied: {decision.reason}"
            )

        order.order_state = decision.target
        order.updated_at = datetime.now()
        self.service.order_repo.update_order(order)

        logger.info(
            f"Order {order_id}: {decision.current} → {decision.target}"
        )
        return {
            'order_id': order_id,
            'previous_state': decision.current,
            'new_state': decision.target,
            'side_effects': decision.side_effects,
        }

    # ================================================================
    # CONVENIENCE — FINALIZE (phases 2 + 3)
    # ================================================================

    async def finalize_order(
        self,
        order_id: int,
        payment_method: str = 'card',
        transaction_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payment_result = await self.process_payment(
            order_id=order_id,
            payment_method=payment_method,
            transaction_details=transaction_details,
        )
        inventory_result = await self.confirm_inventory_for_order(order_id)
        return {
            **payment_result,
            **inventory_result,
            'inventory_deducted': True,
        }

    # ================================================================
    # REMOTE HELPERS (all HTTP calls live here)
    # ================================================================

    async def _check_inventory_availability(
        self, items: List[OrderedItem_API]
    ) -> None:
        """Remote: read-only bulk availability check."""
        product_ids = [item.product_id for item in items]

        availability_response = (
            await self.inventory_client.get_bulk_stock_status(
                product_ids=product_ids
            )
        )
        stock_by_product = self.service.parse_inventory_response(
            availability_response
        )
        logger.info(f"Stock data: {stock_by_product}")

        for item in items:
            product_id = item.product_id
            stock_status = stock_by_product.get(str(product_id), {})
            available_qty = stock_status.get('available_quantity', 0)

            logger.info(
                f"Product {product_id}: available={available_qty}, "
                f"requested={item.ordered_quantity}"
            )

            if available_qty < item.ordered_quantity:
                raise ProductQuantityNotEnoughException(
                    product_id=product_id,
                    requested_quantity=item.ordered_quantity,
                    available_quantity=available_qty,
                )

        logger.info("✅ Inventory availability check passed")

    async def _reserve_inventory(
        self, items: List[OrderedItem]
    ) -> None:
        """Remote: reserve inventory for persisted items."""
        reserve_items = self.service.build_reserve_payload(items)

        reserve_response = await self.inventory_client.reserve_inventory(
            items=reserve_items,
            item_type='ordered_item',
        )

        if isinstance(reserve_response, dict):
            if not reserve_response.get('success', True):
                raise Exception(
                    f"Inventory reservation failed: {reserve_response}"
                )
            success_count = reserve_response.get(
                'success_count', len(items)
            )
            if success_count == 0:
                raise Exception(
                    "Inventory reservation failed: no items reserved"
                )

    async def _safe_release_inventory(
        self, items: List[OrderedItem]
    ) -> None:
        """Remote: best-effort release during rollback. Never raises."""
        try:
            release_items = self.service.build_reserve_payload(items)
            await self.inventory_client.release_inventory(
                items=release_items,
                item_type='ordered_item',
            )
            logger.info("✅ Inventory released")
        except Exception as e:
            logger.error(f"Failed to release inventory: {e}")

    # ================================================================
    # DELETE ORDER (remote release + local delete)
    # ================================================================

    async def delete_order(self, order_id: int) -> bool:
        """
        Orchestrates: load items → delete local → release remote.

        Deletion is not a state transition. Persist first, release
        second, same rationale as cancel_order.
        """
        logger.info(f"Deleting order with ID: {order_id}")
        order = self.service.get_order_by_id(order_id, with_items=True)

        items = list(order.ordered_item or [])

        # Persist first.
        deleted = self.service.delete_order(order_id)

        # Then release.
        if deleted and items:
            try:
                await self._safe_release_inventory(items)
            except Exception:
                logger.error(
                    "Delete succeeded but inventory release failed for "
                    "order %s — reservations are leaked and must be "
                    "reconciled",
                    order_id,
                )

        return deleted


    @staticmethod
    def _as_decimal(value: Any) -> Optional[Decimal]:
        """
        Coerce whatever the finance service returns into a Decimal.

        Handles Decimal (passes through), int, float, and numeric
        strings. Returns None for anything unparseable so the caller
        can decide how to handle it (in `process_payment`, that's a
        PaymentNotConfirmedException).
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _normalize_payment_status(value: Any) -> str:
        """
        Normalize a payment status value into a lowercase string.

        Handles: str, Enum (with or without `.value`), None.
        """
        if value is None:
            return ""
        if isinstance(value, Enum):
            value = value.value
        return str(value).strip().lower()

    async def _reserve_inventory(
        self, items: List[OrderedItem]
    ) -> List[int]:
        """
        Remote: reserve inventory for persisted items.

        Returns the ordered-item IDs that were reserved. On partial
        failure, releases what succeeded and raises — the caller must
        be able to roll back cleanly.
        """
        reserve_items = self.service.build_reserve_payload(items)
        if not reserve_items:
            return []

        reserved_ids = [r["id"] for r in reserve_items if r.get("id")]

        try:
            reserve_response = await self.inventory_client.reserve_inventory(
                items=reserve_items,
                item_type='ordered_item',
            )
        except Exception:
            # The client may have reserved some before failing. Best
            # effort release, then re-raise the original error.
            await self._safe_release_inventory_by_ids(reserved_ids)
            raise

        if isinstance(reserve_response, dict):
            if not reserve_response.get('success', True):
                await self._safe_release_inventory_by_ids(reserved_ids)
                raise Exception(
                    f"Inventory reservation failed: {reserve_response}"
                )
            success_count = reserve_response.get(
                'success_count', len(reserve_items)
            )
            if success_count == 0:
                raise Exception(
                    "Inventory reservation failed: no items reserved"
                )

        return reserved_ids

    async def _safe_release_inventory_by_ids(
        self, item_ids: List[int]
    ) -> None:
        """Remote: best-effort release by ordered-item ID. Never raises."""
        if not item_ids:
            return
        try:
            await self.inventory_client.release_inventory(
                items=[{"id": iid} for iid in item_ids],
                item_type='ordered_item',
            )
            logger.info("✅ Released %d reservations", len(item_ids))
        except Exception as e:
            logger.error(
                "Failed to release reservations %s — may be leaked: %s",
                item_ids, e,
            )


    def _assert_invoice_can_reach_paid(self, invoice: Invoice) -> None:
        """
        Structural check: can this invoice, in principle, move to 'paid'?

        Only the edge existence is checked here — the amount-dependent
        predicate is evaluated at commit time, once `captured_amount` is
        known. If the invoice is already in a state with no edge to
        'paid' (e.g. cancelled, refunded), reject now rather than after
        creating a payment.
        """
        current = self.invoice_policy.normalize(invoice.invoice_status)
        if not self.invoice_policy.is_valid(current):
            raise ValueError(
                f"Invoice cannot be paid: invalid current status "
                f"{current!r}"
            )
        allowed = self.invoice_policy.allowed_targets(current)
        if "paid" not in allowed:
            raise ValueError(
                f"Invoice cannot be paid: no transition {current!r} → "
                f"'paid' (allowed: {sorted(allowed)})"
            )


    def _assert_order_can_reach_processing(self, order: PlacedOrder) -> None:
        """
        Structural check: can this order, in principle, move to
        PROCESSING?

        Checks the edge exists and the entity-derived precondition holds
        (`has_items`). The external-fact precondition (`payment_paid`)
        is evaluated at commit time, once the payment is confirmed.
        """
        current = self.order_policy.normalize(order.order_state)
        if not self.order_policy.is_valid(current):
            raise ValueError(
                f"Order cannot move to PROCESSING: invalid current state "
                f"{current!r}"
            )
        allowed = self.order_policy.allowed_targets(current)
        if "PROCESSING" not in allowed:
            raise ValueError(
                f"Order cannot move to PROCESSING: no transition "
                f"{current!r} → 'PROCESSING' (allowed: {sorted(allowed)})"
            )

        # Entity-derived predicate the policy would also run.
        from policies.placed_order_policy import has_items
        if not has_items(order):
            raise ValueError(
                "Order cannot move to PROCESSING: order has no items"
            )



    def _assert_invoice_has_payable_total(self, invoice: Invoice) -> None:
        """
        Structural check: an invoice with a non-positive grand_total
        cannot go through the payment path. Either it was constructed
        wrongly (a bug) or it's a zero-value invoice that should be
        settled by a different mechanism (comp, waiver) — not by
        creating a payment record for 0.00.

        Rejecting here means no finance record is created for an
        invoice that has nothing to pay.
        """
        total = self._as_decimal(invoice.grand_total)
        if total is None:
            raise ValueError(
                f"Invoice {invoice.invoice_id} cannot be paid: "
                f"grand_total is missing"
            )
        if total <= 0:
            raise ValueError(
                f"Invoice {invoice.invoice_id} cannot be paid: "
                f"grand_total={total} is not positive"
            )