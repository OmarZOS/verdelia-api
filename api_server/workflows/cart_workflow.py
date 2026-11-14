# services/cart_workflow.py
"""
Cart workflow — orchestration layer.

Owns every call that crosses a process boundary:
  - InventoryServiceClient (availability, reserve, confirm, release)
  - FinanceServiceClient    (create payment, confirm payment)

Owns the sequencing of the cart lifecycle:
  Phase 1  create_cart
  Phase 2  process_payment
  Phase 3  confirm_inventory_for_cart
  Finalize finalize_cart  → Phase 2 + Phase 3

CartService (local) is injected. No remote clients live on the service.

Exception boundary:
  Inventory-client exceptions (InventoryClientError and subclasses)
  do not escape this module. They are translated at the workflow
  boundary into cart exceptions (CartInsufficientStockException, etc.)
  so the router can map them to correct HTTP statuses without knowing
  anything about the inventory transport layer.
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import logging

from core.exceptions.handler import InsufficientStockException
from core.exceptions.specific.cart_exceptions import (
    CartCreationFailedException,
    CartInsufficientStockException,
    CartStockRollbackException,
)
from core.exceptions.specific.finance_exceptions import (
    PaymentNotConfirmedException,
)

from storage.wrappers.inventory_client import InventoryServiceClient
from storage.wrappers.inventory_exceptions import (
    InsufficientStockError,
    InventoryClientError,
    InventoryConflictError,
)
from storage.wrappers.finance_client import FinanceServiceClient

from core.models.api_models import (
    Cart_API,
    OrderedItem_API,
    OrderedService_API,
    Delivery_API,
    Person_API,
    Payment_API,
)
from core.models.models import (
    Cart,
    OrderedItem,
    OrderedService,
    Invoice,
    Payment,
)

from policies.cart_policy import CartPolicy
from policies.ordered_item_policy import OrderedItemPolicy
from policies.invoice_policy import InvoicePolicy
from policies.payment_policy import PaymentPolicy
from policies.ordered_service_policy import OrderedServicePolicy

from services.cart_service import CartService, PaymentIntent

from core.logging_config import get_logger

logger = get_logger(__name__)


class CartWorkflow:
    """Orchestration around CartService."""

    def __init__(
        self,
        service: Optional[CartService] = None,
        inventory_client: Optional[InventoryServiceClient] = None,
        finance_client: Optional[FinanceServiceClient] = None,
        cart_policy: Optional[CartPolicy] = None,
        invoice_policy: Optional[InvoicePolicy] = None,
        item_policy: Optional[OrderedItemPolicy] = None,
        service_policy: Optional[OrderedServicePolicy] = None,
        payment_policy: Optional[PaymentPolicy] = None,
    ):
        self.service = service or CartService()
        self.inventory_client = inventory_client or InventoryServiceClient()
        self.finance_client = finance_client or FinanceServiceClient()

        self.cart_policy = cart_policy or CartPolicy()
        self.invoice_policy = invoice_policy or InvoicePolicy()
        self.item_policy = item_policy or OrderedItemPolicy()
        self.service_policy = service_policy or OrderedServicePolicy()
        self.payment_policy = payment_policy or PaymentPolicy()

    # ================================================================
    # PHASE 1 — CREATE CART
    # ================================================================

    async def create_cart(
        self,
        ordered_items: List[OrderedItem_API],
        ordered_services: List[OrderedService_API],
        cart_data: Cart_API,
        delivery: Optional[Delivery_API] = None,
        payment: Optional[Payment_API] = None,
        client: Optional[Person_API] = None,
        provider_id: int = 0,
        seller_user_id: int = 0,
        buyer_user_id: int = 0,
    ) -> Tuple[Dict[str, Any], Cart]:
        logger.info(
            "Creating cart for provider %s, seller %s",
            provider_id, seller_user_id,
        )

        if not ordered_items and not ordered_services:
            raise CartCreationFailedException(
                error="Cart must have at least one item or service",
                provider_id=provider_id,
                seller_id=seller_user_id,
            )

        intent = self.service.detect_payment_intent(cart_data)
        logger.info("Detected payment intent: %s", intent.value)

        created_cart: Optional[Cart] = None
        created_items: List[OrderedItem] = []
        created_services: List[OrderedService] = []
        created_invoice: Optional[Invoice] = None
        inventory_reserved = False

        try:
            # Step 1 — local: validate entities
            logger.info("Step 1: Validating entities...")
            await self.service.validate_entities(
                provider_id, seller_user_id, buyer_user_id
            )

            # Step 2 — local: load catalog
            logger.info("Step 2: Loading products and services...")
            products, services = await self.service.load_products_and_services(
                ordered_items, ordered_services
            )

            # Step 3 — local: plan reservations
            logger.info("Step 3: Building reservation plan...")
            reservation_plan, item_details = (
                await self.service.build_reservation_plan(
                    ordered_items, ordered_services, products, services
                )
            )

            # Step 4 — remote: check inventory availability
            logger.info("Step 4: Validating inventory availability...")
            await self._check_inventory_availability(reservation_plan)

            # Step 5 — local: build cart
            logger.info("Step 5: Building cart...")
            cart, total_price, person_obj = await self.service.build_cart(
                ordered_items=ordered_items,
                ordered_services=ordered_services,
                cart_data=cart_data,
                products=products,
                services=services,
                item_details=item_details,
                provider_id=provider_id,
                seller_user_id=seller_user_id,
                buyer_user_id=buyer_user_id,
                client=client,
            )

            self._transition_cart(
                target="pending",
                is_local=True,
                cart=cart,
            )

            # Step 6 — local: persist cart + invoice
            logger.info("Step 6: Persisting cart...")
            (
                created_cart,
                created_items,
                created_services,
                created_invoice,
            ) = await self.service.persist_cart(cart, total_price, person_obj)

            # Step 7 — remote: reserve inventory
            logger.info("Step 7: Reserving inventory...")
            await self._reserve_inventory(
                reservation_plan, created_items, created_services
            )
            inventory_reserved = True

            # Step 8 — payment if intent declared.
            financial_docs: Dict[str, Any] = {}
            if intent in (PaymentIntent.FULL, PaymentIntent.DEPOSIT):
                logger.info(
                    "Step 8: Processing payment via process_payment..."
                )
                captured_raw = getattr(cart_data, "cart_paid_money", 0)
                captured_dec = self._as_decimal(captured_raw)
                if captured_dec is not None and captured_dec <= 0:
                    captured_dec = None

                financial_docs = await self.process_payment(
                    cart_id=created_cart.cart_id,
                    payment_method=(
                        getattr(cart_data, "cart_payment_method", None)
                        or "cash"
                    ),
                    captured_amount=captured_dec,
                )

                logger.info(
                    "Cart %s: payment succeeded; awaiting delivery "
                    "creation before the checkout transition",
                    created_cart.cart_id,
                )
            else:
                logger.info(
                    "Step 8: No payment requested (intent=%s)",
                    intent.value,
                )

            # Step 9 — remote: confirm reservations
            logger.info("Step 9: Confirming reservations...")
            await self._confirm_reservations(
                created_items, created_services, reservation_plan
            )

            financial_docs["invoice"] = created_invoice

            logger.info("Cart %s creation completed", created_cart.cart_id)
            return financial_docs, created_cart

        except CartInsufficientStockException as e:
            # Availability check failed before anything was persisted
            # or reserved — nothing to roll back.
            logger.error(
                "Cart creation failed — insufficient stock during "
                "availability check: %s", e,
            )
            raise

        except InsufficientStockError as e:
            logger.error(
                "Cart creation failed — insufficient stock during "
                "reservation: %s (operation=%s)", e, e.operation,
            )
            release_error = await self._cleanup_failed_cart(
                created_cart, created_items, created_services,
                inventory_reserved,
            )
            raise CartInsufficientStockException(
                cart_id=created_cart.cart_id if created_cart else None,
                product_id=e.details.get("product_id"),
                requested=e.details.get("requested"),
                available=e.details.get("available"),
                detail=(
                    str(e)
                    + (f"; release_error={release_error}" if release_error else "")
                ),
            ) from e

        except Exception:
            logger.exception("Cart creation failed")
            await self._cleanup_failed_cart(
                created_cart, created_items, created_services,
                inventory_reserved,
            )
            raise


    async def _cleanup_failed_cart(
        self,
        created_cart: Optional[Cart],
        created_items: List[OrderedItem],
        created_services: List[OrderedService],
        inventory_reserved: bool,
    ) -> Optional[Exception]:
        """
        Shared rollback for create_cart. Returns the release error (if
        any) so callers that want to surface it can; never raises.
        """
        release_error: Optional[Exception] = None
        if inventory_reserved:
            try:
                await self._release_inventory(
                    created_items,
                    [
                        c for svc in created_services
                        for c in (svc.product_consumption or [])
                    ],
                )
            except Exception as rel_err:
                release_error = rel_err
                logger.exception(
                    "Inventory release failed during rollback — "
                    "reservations may be leaked"
                )

        try:
            await self.service.rollback_cart_creation(
                created_cart, created_items
            )
        except Exception:
            logger.exception(
                "Cart rollback failed — DB is dirty for cart %s",
                created_cart.cart_id if created_cart else None,
            )

        return release_error

    # ================================================================
    # PHASE 2 — PROCESS PAYMENT
    # ================================================================

    async def process_payment(
        self,
        cart_id: int,
        payment_method: str = "card",
        captured_amount: Optional[Union[Decimal, float, str]] = None,
        transaction_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 2 — orchestrate payment for a cart's invoice.

        Money rule for this method:
        * `captured_amount` may arrive as `str` (query param), `float`
            (legacy caller), or `Decimal` (preferred). It is coerced to
            `Decimal` **once**, at the top, and never converted back to
            `float` until the request body is built.
        * All comparisons (`captured >= total`, the policy decision)
            run in `Decimal`. Floats are not used for money arithmetic.
        * The single `Decimal → float` conversion happens inside
            `build_payment_create_payload` (or immediately before the
            JSON encoding), never before the policy has decided.
        """
        logger.info("Processing payment for cart %s...", cart_id)

        # ── Coerce captured_amount to Decimal once ─────────────────────
        captured_dec: Optional[Decimal] = None
        if captured_amount is not None:
            captured_dec = self._as_decimal(captured_amount)
            if captured_dec is None:
                raise ValueError(
                    f"Invalid captured_amount: {captured_amount!r}"
                )

        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        invoice = self.service.get_invoice_for_cart(cart)

        # Guard 1: invoice already paid
        current_status = self.invoice_policy.normalize(
            invoice.invoice_status or "unpaid"
        )
        if current_status == "paid":
            logger.info("Cart %s invoice already paid — skipping", cart_id)
            return {
                "cart_id": cart_id,
                "invoice_id": invoice.invoice_id,
                "payment_id": None,
                "payment_status": "paid",
            }

        # Guard 2: existing completed payment for this invoice
        existing = self.service.get_completed_payment_for_invoice(
            invoice.invoice_id
        )
        if existing:
            logger.info(
                "Invoice %s already has completed payment %s — skipping",
                invoice.invoice_id, existing.payment_id,
            )
            return {
                "cart_id": cart_id,
                "invoice_id": invoice.invoice_id,
                "payment_id": existing.payment_id,
                "payment_status": existing.payment_status,
            }

        # ── Decide the target in Decimal ───────────────────────────────
        total_dec = self._as_decimal(invoice.grand_total) or Decimal("0")
        
        logger.info(f"Comparing {total_dec} to {captured_dec} for cart {cart_id} invoice {invoice.invoice_id}")
        if captured_dec is None:
            target = "paid"
            captured_for_policy: Optional[Decimal] = None
        else:
            target = "paid" if captured_dec >= total_dec else "partially_paid"
            captured_for_policy = captured_dec

        # Pre-flight: structural check only. `captured_amount=None`
        # is understood by the policy as "don't validate against the
        # total; this is a structural decision".
        invoice_pre = self.invoice_policy.decide_for_invoice(
            invoice,
            target=target,
            captured_amount=captured_for_policy,
        )
        if not invoice_pre.allowed:
            raise ValueError(
                f"Invoice transition denied: {invoice_pre.reason}"
            )

        # ── Build the remote payload ──────────────────────────────────
        # `amount` stays Decimal until the last possible moment. The
        # float conversion, if any, happens inside the payload builder
        # (see `build_payment_create_payload`).
        amount_dec = captured_dec if captured_dec is not None else total_dec
        payment_payload = self.service.build_payment_create_payload(
            cart=cart,
            invoice=invoice,
            payment_method=payment_method,
            captured_amount=amount_dec,
        )
        payment_response = await self.finance_client.create_payment(
            payment_payload
        )
        logger.info("Payment %s created", payment_response.id)

        # Remote: confirm payment
        details = (
            transaction_details
            or self.service.build_payment_transaction_details(
                cart=cart,
                invoice=invoice,
                payment_method=payment_method,
            )
        )
        confirmed = await self.finance_client.confirm_payment(
            payment_id=payment_response.id,
            transaction_details=details,
        )
        logger.info(
            "Payment %s confirmed (status=%s)",
            confirmed.id, confirmed.status,
        )

        # Sanity: confirm must not return a different payment
        if confirmed.id != payment_response.id:
            raise ValueError(
                f"create/confirm returned different payment ids: "
                f"{payment_response.id} vs {confirmed.id}"
            )

        # Sanity: confirm must have actually completed
        confirmed_status = self._normalize_payment_status(confirmed.status)
        if confirmed_status not in ("completed", "confirmed", "paid"):
            raise PaymentNotConfirmedException(
                payment_id=confirmed.id,
                status=confirmed.status,
                invoice_id=invoice.invoice_id,
            )

        # ── Commit: does the captured amount clear the invoice? ───────
        captured = self._as_decimal(confirmed.amount)
        if captured is None or captured <= 0:
            raise PaymentNotConfirmedException(
                payment_id=confirmed.id,
                # `!s` on a Decimal renders "803.71", not the float noise.
                status=f"amount={captured!s}",
                invoice_id=invoice.invoice_id,
            )

        # Pass Decimal to the policy — this is the comparison that
        # decides whether the invoice can move to `paid`. Do NOT
        # `float()` it here.
        invoice_commit = self.invoice_policy.decide_for_invoice(
            invoice,
            target=target,
            captured_amount=captured,
        )
        if not invoice_commit.allowed:
            raise ValueError(
                f"Payment captured {captured} but invoice cannot "
                f"move to {target!r}: {invoice_commit.reason}"
            )

        # Local: apply the invoice decision
        self.service.apply_invoice_status(invoice, invoice_commit.target)

        logger.info(
            "Applied transition: invoice %s → %s",
            invoice_commit.current, invoice_commit.target,
        )

        return {
            "cart_id": cart.cart_id,
            "invoice_id": invoice.invoice_id,
            "payment_id": confirmed.id,
            "payment_status": confirmed.status,
        }

    # ================================================================
    # PHASE 3 — CONFIRM INVENTORY
    # ================================================================

    async def confirm_inventory_for_cart(
        self, cart_id: int
    ) -> Dict[str, Any]:
        """Phase 3 orchestration (by cart id)."""
        logger.info("Confirming inventory for cart %s...", cart_id)

        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        items = list(cart.ordered_item or [])
        services = list(cart.ordered_service or [])

        if not items and not services:
            logger.info("Cart %s has no items to confirm", cart_id)
            return {
                "cart_id": cart_id,
                "items_confirmed": 0,
                "success": True,
            }

        return await self.confirm_inventory_for_cart_entities(
            items, services, cart_id=cart_id
        )

    async def confirm_inventory_for_cart_entities(
        self,
        items: List[Any],
        services: List[Any],
        *,
        cart_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Phase 3 orchestration (by entities)."""
        ordered_payload = self._build_confirm_ordered_payload(items)
        consumption_payload = self._build_confirm_consumption_payload(services)

        if not ordered_payload and not consumption_payload:
            logger.info("No items to confirm for cart %s", cart_id)
            return {
                "cart_id": cart_id,
                "items_confirmed": 0,
                "success": True,
            }

        try:
            await self.inventory_client.bulk_confirm(
                ordered_payload,
                consumption_payload,
            )
        except InsufficientStockError as e:
            raise CartInsufficientStockException(
                cart_id=cart_id,
                product_id=e.details.get("product_id"),
                requested=e.details.get("requested"),
                available=e.details.get("available"),
                detail=str(e),
            ) from e

        total = len(ordered_payload) + len(consumption_payload)
        logger.info(
            "Inventory confirmed (%d entries) for cart %s",
            total, cart_id,
        )
        return {
            "cart_id": cart_id,
            "items_confirmed": total,
            "success": True,
        }

    # ================================================================
    # EXPLICIT CART TRANSITIONS (policy-gated)
    # ================================================================

    async def mark_cart_pending(self, cart_id: int) -> Dict[str, Any]:
        """open → pending, gated by CartPolicy."""
        return self._transition_cart(cart_id, target="pending")

    async def mark_cart_checkout(
        self,
        cart_id: int,
        *,
        invoice_issued: bool = True,
        delivery_created: bool = True,
    ) -> Dict[str, Any]:
        """pending → checkout, gated by CartPolicy."""
        return self._transition_cart(
            cart_id,
            target="checkout",
            invoice_issued=invoice_issued,
            delivery_created=delivery_created,
        )

    async def mark_cart_completed(
        self,
        cart_id: int,
        *,
        fully_fulfilled: bool = True,
    ) -> Dict[str, Any]:
        """checkout/partial → completed, gated by CartPolicy."""
        return self._transition_cart(
            cart_id,
            target="completed",
            fully_fulfilled=fully_fulfilled,
        )

    async def mark_cart_partial(
        self,
        cart_id: int,
        *,
        partially_fulfilled: bool = True,
    ) -> Dict[str, Any]:
        """pending/checkout → partial, gated by CartPolicy."""
        return self._transition_cart(
            cart_id,
            target="partial",
            partially_fulfilled=partially_fulfilled,
        )

    async def mark_cart_abandoned(
        self,
        cart_id: int,
        *,
        stale: bool = True,
    ) -> Dict[str, Any]:
        """open/pending → abandoned, gated by CartPolicy."""
        return self._transition_cart(
            cart_id,
            target="abandoned",
            stale=stale,
        )

    async def reopen_cart(self, cart_id: int) -> Dict[str, Any]:
        """abandoned → open, gated by CartPolicy."""
        return self._transition_cart(cart_id, target="open")

    async def cancel_cart(
        self,
        cart_id: int,
        *,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        * → canceled, gated by CartPolicy.

        Persist the status change first, then release. If the persist
        fails, no release happens and the cart stays live. If the
        release fails, the cancel still stands and we log an explicit
        reconciliation error.
        """
        cart = self.service.get_cart_by_id(cart_id, eager_load=True)

        decision = self.cart_policy.decide_for_cart(cart, target="canceled")
        if not decision.allowed:
            raise ValueError(f"Cart transition denied: {decision.reason}")

        items = list(cart.ordered_item or [])
        services = list(cart.ordered_service or [])
        consumptions = [
            c for svc in services for c in (svc.product_consumption or [])
        ]

        # Persist first.
        result = self._apply_cart_decision(cart, decision)

        # Then release.
        if items or consumptions:
            try:
                await self._release_inventory(items, consumptions)
            except Exception:
                logger.error(
                    "Cancel succeeded but inventory release failed for "
                    "cart %s — reservations are leaked and must be "
                    "reconciled",
                    cart_id,
                )

        result["reason"] = reason
        return result

    # ================================================================
    # EXPLICIT ITEM / SERVICE TRANSITIONS (policy-gated)
    # ================================================================

    async def mark_item_shipped(self, item_id: int) -> Dict[str, Any]:
        """processing → shipped, gated by OrderedItemPolicy."""
        item = self.service.get_ordered_item(item_id)

        decision = self.item_policy.decide_for_item(
            item, target="shipped", delivery_confirmed=True
        )
        if not decision.allowed:
            raise ValueError(f"Item transition denied: {decision.reason}")

        item.ordered_item_delivery_status = decision.target
        self.service.persist_ordered_item(item)

        return self._decision_to_dict(item_id, decision)

    async def mark_service_scheduled(
        self,
        service_id: int,
        *,
        scheduled_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """processing → scheduled, gated by OrderedServicePolicy."""
        service = self.service.get_ordered_service(service_id)

        extras: Dict[str, Any] = {}
        if scheduled_at is not None:
            extras["scheduled_at"] = scheduled_at
            service.ordered_service_scheduled_at = scheduled_at

        decision = self.service_policy.decide_for_service(
            service, target="scheduled", **extras
        )
        if not decision.allowed:
            raise ValueError(f"Service transition denied: {decision.reason}")

        service.ordered_service_delivery_status = decision.target
        self.service.persist_ordered_service(service)

        return self._decision_to_dict(service_id, decision)

    # ================================================================
    # CONVENIENCE — FINALIZE (phases 2 + 3)
    # ================================================================

    async def finalize_cart(
        self,
        cart_id: int,
        payment_method: str = "card",
        captured_amount: Optional[Union[Decimal, float, str]] = None,
        transaction_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convenience: run Phase 2 (payment) and Phase 3 (inventory
        confirmation) back-to-back. `captured_amount` is forwarded to
        `process_payment` unchanged; it is coerced to `Decimal` there.
        """
        payment_result = await self.process_payment(
            cart_id=cart_id,
            payment_method=payment_method,
            captured_amount=captured_amount,
            transaction_details=transaction_details,
        )
        inventory_result = await self.confirm_inventory_for_cart(cart_id)
        return {
            **payment_result,
            **inventory_result,
            "inventory_deducted": True,
        }

    # ================================================================
    # INTERNAL — cart transition core
    # ================================================================

    def _transition_cart(
        self,
        cart_id: Optional[int] = None,
        target: str = "",
        is_local: bool = False,
        cart: Optional[Cart] = None,
        **extras: Any,
    ) -> Dict[str, Any]:
        """
        Shared core for every `mark_cart_*` method.

        Two modes, chosen by the caller:

        - Pass `cart=<Cart>`: apply the decision to the in-memory
          object the caller already holds, without any database
          lookup. Used by `create_cart`, where the cart is being
          assembled and shouldn't be touched in the DB until the
          whole flow succeeds. Combine with `is_local=True` to skip
          persistence.

        - Pass `cart_id=<int>`: load the cart from the database,
          apply the decision, and persist the new status. Used by
          the standalone transition endpoints.

        If both are supplied, `cart` wins and `cart_id` is ignored.
        """
        if cart is None:
            cart = self.service.get_cart_by_id(cart_id, eager_load=True)

        decision = self.cart_policy.decide_for_cart(
            cart, target=target, **extras
        )
        if not decision.allowed:
            raise ValueError(
                f"Cart transition denied: {decision.reason}"
            )

        if is_local:
            return self._apply_cart_decision_locally(cart, decision)
        return self._apply_cart_decision(cart, decision)

    def _apply_cart_decision_locally(
        self, cart: Cart, decision
    ) -> Dict[str, Any]:
        """Apply the decision to an in-memory cart. No DB write."""
        cart.cart_status = decision.target
        cart.updated_at = datetime.now()

        logger.info(
            "Cart %s: %s → %s (local, side effects: %s)",
            cart.cart_id, decision.current, decision.target,
            decision.side_effects,
        )
        return {
            "cart_id": cart.cart_id,
            "previous_status": decision.current,
            "new_status": decision.target,
            "side_effects": decision.side_effects,
            "persisted": False,
        }

    def _apply_cart_decision(
        self, cart: Cart, decision
    ) -> Dict[str, Any]:
        """Persist the cart's new status per a policy decision."""
        cart.cart_status = decision.target
        cart.updated_at = datetime.now()
        self.service.cart_repo.update_cart(cart)

        logger.info(
            "Cart %s: %s → %s (side effects: %s)",
            cart.cart_id, decision.current, decision.target,
            decision.side_effects,
        )
        return {
            "cart_id": cart.cart_id,
            "previous_status": decision.current,
            "new_status": decision.target,
            "side_effects": decision.side_effects,
            "persisted": True,
        }

    @staticmethod
    def _decision_to_dict(entity_id: int, decision) -> Dict[str, Any]:
        return {
            "entity_id": entity_id,
            "previous_status": decision.current,
            "new_status": decision.target,
            "side_effects": decision.side_effects,
        }

    # ================================================================
    # INTERNAL — remote helpers
    # ================================================================

    async def _check_inventory_availability(
        self, reservation_plan: Dict[int, Dict]
    ) -> None:
        """Remote: read-only bulk availability check."""
        if not reservation_plan:
            return

        product_ids = list(reservation_plan.keys())
        availability_response = (
            await self.inventory_client.get_bulk_stock_status(
                product_ids=product_ids
            )
        )
        stock_by_product = self.service.parse_inventory_response(
            availability_response
        )

        for product_id, plan in reservation_plan.items():
            stock_data = stock_by_product.get(str(product_id), {})
            available_qty = stock_data.get("available_quantity", 0)
            requested_qty = plan["quantity"]
            if available_qty < requested_qty:
                raise CartInsufficientStockException(
                    product_id=product_id,
                    requested=requested_qty,
                    available=available_qty,
                )

        logger.info("Inventory availability check passed")

    async def _reserve_inventory(
        self,
        reservation_plan: Dict[int, Dict],
        created_items: List[OrderedItem],
        created_services: List[OrderedService],
    ) -> None:
        """
        Remote: reserve inventory for persisted items + consumptions.

        Idempotency guard: if an ordered item is already reserved
        (from a previous failed attempt that didn't release
        cleanly), release it before re-reserving. This is a no-op
        on a fresh cart and a self-heal on a retry.
        """
        if not reservation_plan:
            logger.info("No items to reserve")
            return

        # ── Idempotency guard ────────────────────────────────────────
        stale_items: List[OrderedItem] = [
            item for item in created_items
            if (item.reserved_quantity or 0) > 0
        ]
        if stale_items:
            logger.warning(
                "Ordered items already reserved from a previous attempt: %s. "
                "Releasing before re-reserve.",
                [i.id_ordered_item for i in stale_items],
            )
            try:
                await self._release_inventory(stale_items, [])
            except InventoryConflictError as conflict:
                # 409 "no matching reservation" means the reservation
                # doesn't exist on the server. That's already the state
                # we want. Any other conflict is a real failure.
                logger.info(
                    "Stale reservation already gone on the server (%s) — "
                    "proceeding with reserve",
                    conflict,
                )
            except Exception:
                logger.exception(
                    "Failed to release stale reservations for items %s — "
                    "aborting to avoid double-reserve",
                    [i.id_ordered_item for i in stale_items],
                )
                raise CartStockRollbackException(
                    cart_id=stale_items[0].cart_id,
                    error="Stale reservations could not be released",
                )
            for item in stale_items:
                item.reserved_quantity = 0

        # ── Reserve ordered items ───────────────────────────────────
        ordered_reserve_items: List[Dict[str, Any]] = [
            {
                "id": item.id_ordered_item,
                "quantity": str(item.ordered_quantity),
                "item_type": "ordered_item",
            }
            for item in created_items
            if item.ordered_quantity and item.ordered_quantity > 0
        ]

        if ordered_reserve_items:
            await self.inventory_client.reserve_inventory(
                items=ordered_reserve_items,
                item_type="ordered_item",
            )
            logger.info(
                "Reserved %d ordered items",
                len(ordered_reserve_items),
            )

        # ── Reserve consumptions ────────────────────────────────────
        consumption_reserve_items: List[Dict[str, Any]] = []
        for service in created_services:
            for consumption in service.product_consumption or []:
                pid = consumption.consumed_product_id
                qty = 0
                plan = reservation_plan.get(pid, {})
                for source in plan.get("sources", []):
                    if (
                        source.get("type") == "consumption"
                        and source.get("id") == consumption.requirement_id
                    ):
                        qty = source.get("quantity", 0)
                        break
                if qty and qty > 0:
                    consumption_reserve_items.append({
                        "id": consumption.id_product_consumption,
                        "quantity": str(qty),
                        "item_type": "consumption",
                    })

        if consumption_reserve_items:
            try:
                await self.inventory_client.reserve_inventory(
                    items=consumption_reserve_items,
                    item_type="consumption",
                )
                logger.info(
                    "Reserved %d consumptions",
                    len(consumption_reserve_items),
                )
            except Exception:
                # Undo the ordered-item reserve we just did. If the
                # release fails, the caller must know — otherwise
                # the items stay reserved and the next attempt will
                # hit the same InventoryConflictError.
                if ordered_reserve_items:
                    try:
                        await self.inventory_client.release_inventory(
                            items=ordered_reserve_items,
                            item_type="ordered_item",
                        )
                    except Exception:
                        logger.exception(
                            "Failed to release ordered items after "
                            "consumption reserve failure — reservations "
                            "are now leaked"
                        )
                        raise CartStockRollbackException(
                            cart_id=(
                                created_items[0].cart_id
                                if created_items else None
                            ),
                            error=(
                                "Consumption reserve failed and the "
                                "ordered-item reserve could not be "
                                "released"
                            ),
                        )
                raise


    async def _release_inventory(
        self,
        items: List[Any],
        consumptions: List[Any],
    ) -> None:
        """
        Remote: release inventory. Raises on failure.

        Renamed from `_safe_release_inventory` — the previous version
        swallowed every exception, which let rollback paths pretend
        they had cleaned up when they hadn't. Callers that genuinely
        want best-effort must catch the exception themselves.
        """
        ordered_release: List[Dict[str, Any]] = []
        for item in items or []:
            iid = getattr(item, "id_ordered_item", None) or (
                item.get("id") if isinstance(item, dict) else None
            )
            qty = getattr(item, "ordered_quantity", None) or (
                item.get("quantity") if isinstance(item, dict) else None
            )
            pid = getattr(item, "product_id", None) or (
                item.get("product_id") if isinstance(item, dict) else None
            )
            if iid:
                ordered_release.append({
                    "id": iid,
                    "quantity": str(qty),
                    "product_id": pid,
                })

        if ordered_release:
            await self.inventory_client.release_inventory(
                items=ordered_release,
                item_type="ordered_item",
            )
            logger.info(
                "Released %d ordered items", len(ordered_release)
            )

        consumption_release: List[Dict[str, Any]] = []
        for c in consumptions or []:
            cid = getattr(c, "id_product_consumption", None) or (
                c.get("id") if isinstance(c, dict) else None
            )
            qty = getattr(c, "product_reserved_quantity", 0) or (
                c.get("quantity", 0) if isinstance(c, dict) else 0
            )
            if cid:
                consumption_release.append({
                    "id": cid,
                    "quantity": str(qty),
                })

        if consumption_release:
            await self.inventory_client.release_inventory(
                items=consumption_release,
                item_type="consumption",
            )
            logger.info(
                "Released %d consumptions", len(consumption_release)
            )

    async def _safe_release_inventory(
        self,
        items: List[Any],
        consumptions: List[Any],
    ) -> None:
        """
        Best-effort release — for rollback paths that must not mask
        the original exception. Logs and continues on failure.

        Use `_release_inventory` when the release must succeed.
        """
        try:
            await self._release_inventory(items, consumptions)
        except Exception:
            logger.exception(
                "Best-effort inventory release failed — reservations "
                "may be leaked"
            )

    async def _confirm_reservations(
        self,
        created_items: List[OrderedItem],
        created_services: List[OrderedService],
        reservation_plan: Dict[int, Dict],
    ) -> None:
        """Remote: confirm the reservations that were just created."""
        ordered_payload: List[Dict[str, Any]] = [
            {"id": item.id_ordered_item, "quantity": str(item.ordered_quantity)}
            for item in created_items
            if item.ordered_quantity and item.ordered_quantity > 0
        ]

        consumption_payload: List[Dict[str, Any]] = []
        for service in created_services:
            service = self.service.get_ordered_service(service.ordered_service_id)
            for consumption in service.product_consumption or []:
                pid = consumption.consumed_product_id
                plan = reservation_plan.get(pid, {})
                for source in plan.get("sources", []):
                    if (
                        source.get("type") == "consumption"
                        and source.get("id") == consumption.requirement_id
                    ):
                        qty = source.get("quantity", 0)
                        if qty and qty > 0:
                            consumption_payload.append({
                                "id": consumption.id_product_consumption,
                                "quantity": str(qty),
                            })
                        break

        await self.inventory_client.bulk_confirm(
            ordered_payload,
            consumption_payload,
        )

    # async def _safe_release_inventory(
    #     self,
    #     items: List[Any],
    #     consumptions: List[Any],
    # ) -> None:
    #     """Remote: best-effort release. Never raises."""
    #     try:
    #         ordered_release: List[Dict[str, Any]] = []
    #         for item in items or []:
    #             iid = getattr(item, "id_ordered_item", None) or (
    #                 item.get("id") if isinstance(item, dict) else None
    #             )
    #             qty = getattr(item, "ordered_quantity", None) or (
    #                 item.get("quantity") if isinstance(item, dict) else None
    #             )
    #             pid = getattr(item, "product_id", None) or (
    #                 item.get("product_id") if isinstance(item, dict) else None
    #             )
    #             if iid:
    #                 ordered_release.append({
    #                     "id": iid,
    #                     "quantity": qty,
    #                     "product_id": pid,
    #                 })

    #         if ordered_release:
    #             await self.inventory_client.release_inventory(
    #                 items=ordered_release,
    #                 item_type="ordered_item",
    #             )

    #         consumption_release: List[Dict[str, Any]] = []
    #         for c in consumptions or []:
    #             cid = getattr(c, "id_product_consumption", None) or (
    #                 c.get("id") if isinstance(c, dict) else None
    #             )
    #             qty = getattr(c, "product_reserved_quantity", 0) or (
    #                 c.get("quantity", 0) if isinstance(c, dict) else 0
    #             )
    #             if cid:
    #                 consumption_release.append({
    #                     "id": cid,
    #                     "quantity": qty,
    #                 })

    #         if consumption_release:
    #             await self.inventory_client.release_inventory(
    #                 items=consumption_release,
    #                 item_type="consumption",
    #             )

    #         logger.info("Inventory released")
    #     except Exception:
    #         logger.exception("Failed to release inventory")

    # ================================================================
    # INTERNAL — local payload helpers
    # ================================================================

    @staticmethod
    def _build_confirm_ordered_payload(
        items: List[Any],
    ) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for item in items or []:
            if isinstance(item, dict):
                iid = item.get("id") or item.get("id_ordered_item")
                qty = item.get("quantity") or item.get("ordered_quantity")
            else:
                iid = getattr(item, "id_ordered_item", None)
                qty = getattr(item, "ordered_quantity", None)
            if iid and qty and qty > 0:
                payload.append({"id": iid, "quantity": str(qty)})
        return payload

    @staticmethod
    def _build_confirm_consumption_payload(
        services: List[Any],
    ) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for service in services or []:
            if isinstance(service, dict):
                consumptions = service.get("product_consumption", []) or []
            else:
                consumptions = getattr(service, "product_consumption", None) or []
            for c in consumptions:
                if isinstance(c, dict):
                    cid = c.get("id") or c.get("id_product_consumption")
                    qty = (
                        c.get("quantity")
                        or c.get("product_reserved_quantity", 0)
                    )
                else:
                    cid = getattr(c, "id_product_consumption", None)
                    qty = getattr(c, "product_reserved_quantity", 0)
                if cid and qty and qty > 0:
                    payload.append({"id": cid, "quantity": str(qty)})
        return payload

    # ================================================================
    # SMALL HELPERS
    # ================================================================

    @staticmethod
    def _as_decimal(value: Any) -> Optional[Decimal]:
        """
        Coerce to Decimal for money arithmetic.

        Accepted inputs:
        * Decimal        — passthrough
        * int            — Decimal(int) (exact)
        * float          — Decimal(str(f)) so we get the shortest
                            round-trip representation the wire intended,
                            NOT the binary expansion
        * str            — parsed, must be a valid finite Decimal

        Rejects non-finite values (NaN, Infinity). A malformed finance
        response with `"amount": "Infinity"` would otherwise poison every
        downstream comparison.

        Returns None when the value cannot be interpreted as money, so
        callers can branch on "unusable" vs "zero".
        """
        if value is None:
            return None

        if isinstance(value, Decimal):
            d = value
        elif isinstance(value, bool):
            # bool is an int subclass; a payment amount of True/False is
            # a bug, not a quantity.
            return None
        elif isinstance(value, int):
            d = Decimal(value)
        elif isinstance(value, float):
            # Reject non-finite floats before they reach Decimal.
            if value != value or value in (float("inf"), float("-inf")):
                return None
            # `str(float)` gives the shortest round-trip ("803.71"),
            # `Decimal(float)` would give the full binary expansion.
            d = Decimal(str(value))
        elif isinstance(value, str):
            try:
                d = Decimal(value)
            except (InvalidOperation, ValueError, TypeError):
                return None
        else:
            return None

        if not d.is_finite():
            return None
        return d

    @staticmethod
    def _normalize_payment_status(value: Any) -> str:
        from enum import Enum as _Enum
        if value is None:
            return ""
        if isinstance(value, _Enum):
            value = value.value
        return str(value).strip().lower()

    # ================================================================
    # DELETE CART
    # ================================================================

    async def delete_cart(
        self, cart_id: int, force_delete: bool = False
    ) -> bool:
        """
        Orchestrates: persist delete → release remote (if needed).

        Release is skipped when the cart is already in a terminal
        state (canceled/completed) whose transition already released
        inventory. This avoids the double-release that occurs when
        cancel is followed by archive/delete.
        """
        logger.info("Deleting cart %s (force=%s)", cart_id, force_delete)

        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        items = list(cart.ordered_item or [])
        services = list(cart.ordered_service or [])
        consumptions = [
            c for svc in services for c in (svc.product_consumption or [])
        ]

        already_released = (
            self.cart_policy.normalize(cart.cart_status)
            in ("canceled", "cancelled", "completed", "abandoned")
        )

        # Persist first.
        deleted = self.service.cart_repo.delete_cart_by_id_sync(cart_id)

        # Then release, only if not already released by a prior
        # transition.
        if deleted and (items or consumptions) and not already_released:
            try:
                await self._release_inventory(items, consumptions)
            except Exception:
                logger.error(
                    "Delete succeeded but inventory release failed for "
                    "cart %s — reservations are leaked and must be "
                    "reconciled",
                    cart_id,
                )

        return deleted