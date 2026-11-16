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

Delivery is OPTIONAL. A cart with no delivery lines can go
pending → checkout → completed as soon as its invoice settles and its
lines are done.

CartService (local) is injected. No remote clients live on the service.

Exception boundary:
  Inventory-client exceptions (InventoryClientError and subclasses)
  do not escape this module. They are translated at the workflow
  boundary into cart exceptions (CartInsufficientStockException, etc.)
  so the router can map them to correct HTTP statuses without knowing
  anything about the inventory transport layer.
"""

from decimal import Decimal, InvalidOperation
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
                consumption_snapshot,
            ) = await self.service.persist_cart(cart, total_price, person_obj)

            # Step 7 — remote: reserve inventory
            logger.info("Step 7: Reserving inventory...")
            await self._reserve_inventory(
                reservation_plan, created_items, created_services
            )
            inventory_reserved = True

            # Step 8 — payment if intent declared.
            financial_docs: Dict[str, Any] = {}
            payment_succeeded = False
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
                payment_succeeded = True
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

            # Step 10 — try to advance the cart through its next
            # natural state now that payment (if any) has settled.
            # `advance_cart_state` checks both the invoice state and
            # the cart lines; delivery is optional.
            if payment_succeeded or created_invoice is not None:
                advanced = await self.advance_cart_state(
                    created_cart.cart_id,
                )
                if advanced.get("new_status") in ("checkout", "completed"):
                    created_cart = self.service.get_cart_by_id(
                        created_cart.cart_id, eager_load=True
                    )
                else:
                    logger.info(
                        "Cart %s not yet advanced: %s",
                        created_cart.cart_id,
                        advanced.get("reason", "no transition"),
                    )

            financial_docs["invoice"] = created_invoice

            logger.info("Cart %s creation completed", created_cart.cart_id)
            return financial_docs, created_cart

        except CartInsufficientStockException as e:
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
        consumption_snapshot: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Exception]:
        release_error: Optional[Exception] = None
        if inventory_reserved:
            try:
                await self._release_inventory(
                    created_items,
                    list(consumption_snapshot or []),
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

        Money rule:
        * `captured_amount` may arrive as `str`, `float`, or `Decimal`.
          It is coerced to `Decimal` once, at the top.
        * All comparisons run in `Decimal`.
        * The single `Decimal → float` conversion happens inside
          `build_payment_create_payload` (or just before JSON).

        After the invoice settles, this method advances the cart to
        `checkout` if it's currently `pending` (delivery is optional).
        """
        logger.info("Processing payment for cart %s...", cart_id)

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
            await self.advance_cart_state(cart_id)
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
            await self.advance_cart_state(cart_id)
            return {
                "cart_id": cart_id,
                "invoice_id": invoice.invoice_id,
                "payment_id": existing.payment_id,
                "payment_status": existing.payment_status,
            }

        total_dec = self._as_decimal(invoice.grand_total) or Decimal("0")

        logger.info(
            "Comparing %s to %s for cart %s invoice %s",
            total_dec, captured_dec, cart_id, invoice.invoice_id,
        )
        if captured_dec is None:
            target = "paid"
            captured_for_policy: Optional[Decimal] = None
        else:
            target = "paid" if captured_dec >= total_dec else "partially_paid"
            captured_for_policy = captured_dec

        invoice_pre = self.invoice_policy.decide_for_invoice(
            invoice,
            target=target,
            captured_amount=captured_for_policy,
        )
        if not invoice_pre.allowed:
            raise ValueError(
                f"Invoice transition denied: {invoice_pre.reason}"
            )

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

        if confirmed.id != payment_response.id:
            raise ValueError(
                f"create/confirm returned different payment ids: "
                f"{payment_response.id} vs {confirmed.id}"
            )

        confirmed_status = self._normalize_payment_status(confirmed.status)
        if confirmed_status not in ("completed", "confirmed", "paid"):
            raise PaymentNotConfirmedException(
                payment_id=confirmed.id,
                status=confirmed.status,
                invoice_id=invoice.invoice_id,
            )

        captured = self._as_decimal(confirmed.amount)
        if captured is None or captured <= 0:
            raise PaymentNotConfirmedException(
                payment_id=confirmed.id,
                status=f"amount={captured!s}",
                invoice_id=invoice.invoice_id,
            )

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

        self.service.apply_invoice_status(invoice, invoice_commit.target)

        logger.info(
            "Applied transition: invoice %s → %s",
            invoice_commit.current, invoice_commit.target,
        )

        # Advance the cart now that the invoice is settled. Delivery
        # is optional, so `pending → checkout` will fire.
        await self.advance_cart_state(cart_id)

        return {
            "cart_id": cart.cart_id,
            "invoice_id": invoice.invoice_id,
            "payment_id": confirmed.id,
            "payment_status": confirmed.status,
        }

    # ================================================================
    # ADVANCE — the "next natural state" helper
    # ================================================================

    async def advance_cart_state(self, cart_id: int) -> Dict[str, Any]:
        """
        Attempt the cart's next natural transition based on its
        current state, its invoice, and its line-item statuses.

        - pending → checkout: fires as soon as the cart has an
          invoice (delivery is optional).
        - checkout → completed: fires when every line is delivered
          or has no delivery obligation.
        - checkout → partial: fires when some lines are delivered
          and others are still outstanding.
        - pending → partial: same, for carts whose lines started
          being delivered before checkout.

        Safe to call multiple times; if no transition applies, it
        returns a no-op result.
        """
        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        current = self.cart_policy.normalize(cart.cart_status or "open")

        if current == "pending":
            # Try checkout first. `checkout_ready` only requires an
            # invoice row on the cart.
            try:
                return self._transition_cart(
                    cart_id=cart_id,
                    target="checkout",
                    invoice_issued=True,
                    delivery_created=False,
                )
            except ValueError as e:
                logger.debug(
                    "Cart %s cannot advance to checkout yet: %s",
                    cart_id, e,
                )
            # Fall through to partial.
            try:
                return self._transition_cart(
                    cart_id=cart_id,
                    target="partial",
                    partially_fulfilled=True,
                )
            except ValueError as e:
                logger.debug(
                    "Cart %s cannot advance to partial yet: %s",
                    cart_id, e,
                )

        if current in ("checkout", "partial"):
            try:
                return self._transition_cart(
                    cart_id=cart_id,
                    target="completed",
                    fully_fulfilled=True,
                )
            except ValueError as e:
                logger.debug(
                    "Cart %s cannot advance to completed yet: %s",
                    cart_id, e,
                )
            if current == "checkout":
                try:
                    return self._transition_cart(
                        cart_id=cart_id,
                        target="partial",
                        partially_fulfilled=True,
                    )
                except ValueError as e:
                    logger.debug(
                        "Cart %s cannot advance to partial yet: %s",
                        cart_id, e,
                    )

        return {
            "cart_id": cart_id,
            "new_status": None,
            "reason": f"no transition from {current}",
        }

    # ================================================================
    # PHASE 3 — CONFIRM INVENTORY
    # ================================================================

    async def confirm_inventory_for_cart(
        self, cart_id: int
    ) -> Dict[str, Any]:
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
        ordered_payload = self._build_confirm_ordered_payload(items)

        # Consumptions come from the repo, as plain dicts — never from
        # the ORM relationship on `services`. The services were loaded by
        # a session that has since closed; reading `.product_consumption`
        # would detach-error.
        consumption_snapshot: List[Dict[str, Any]] = []
        if cart_id is not None:
            consumption_snapshot = (
                self.service.get_consumption_snapshot_for_cart(cart_id)
            )
        consumption_payload = self._build_confirm_consumption_payload(
            consumption_snapshot
        )

        if not ordered_payload and not consumption_payload:
            return {
                "cart_id": cart_id,
                "items_confirmed": 0,
                "success": True,
            }

        try:
            await self.inventory_client.bulk_confirm(
                ordered_payload, consumption_payload,
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
        return {
            "cart_id": cart_id,
            "items_confirmed": total,
            "success": True,
        }


    # ================================================================
    # EXPLICIT CART TRANSITIONS (policy-gated)
    # ================================================================

    async def mark_cart_pending(self, cart_id: int) -> Dict[str, Any]:
        return self._transition_cart(cart_id, target="pending")

    async def mark_cart_checkout(
        self,
        cart_id: int,
        *,
        invoice_issued: bool = True,
        delivery_created: bool = False,   # optional now
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
        return self._transition_cart(
            cart_id,
            target="abandoned",
            stale=stale,
        )

    async def reopen_cart(self, cart_id: int) -> Dict[str, Any]:
        return self._transition_cart(cart_id, target="open")

    async def cancel_cart(
        self, cart_id: int, *, reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        decision = self.cart_policy.decide_for_cart(cart, target="canceled")
        if not decision.allowed:
            raise ValueError(f"Cart transition denied: {decision.reason}")

        items = list(cart.ordered_item or [])
        consumption_snapshot = (
            self.service.get_consumption_snapshot_for_cart(cart_id)
        )

        result = self._apply_cart_decision(cart, decision)

        if items or consumption_snapshot:
            try:
                await self._release_inventory(items, consumption_snapshot)
            except Exception:
                logger.error(
                    "Cancel succeeded but inventory release failed for "
                    "cart %s — reservations are leaked",
                    cart_id,
                )

        result["reason"] = reason
        return result

    # ================================================================
    # EXPLICIT ITEM / SERVICE TRANSITIONS
    # ================================================================

    async def mark_item_shipped(self, item_id: int) -> Dict[str, Any]:
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
        if not reservation_plan:
            logger.info("No items to reserve")
            return

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
        ordered_payload: List[Dict[str, Any]] = [
            {"id": item.id_ordered_item, "quantity": str(item.ordered_quantity)}
            for item in created_items
            if item.ordered_quantity and item.ordered_quantity > 0
        ]

        consumption_payload: List[Dict[str, Any]] = []
        for service in created_services:
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
        consumption_snapshot: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for row in consumption_snapshot or []:
            cid = row.get("id")
            qty = row.get("quantity", 0)
            if cid and qty and qty > 0:
                payload.append({"id": cid, "quantity": str(qty)})
        return payload

    # ================================================================
    # SMALL HELPERS
    # ================================================================

    @staticmethod
    def _as_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None

        if isinstance(value, Decimal):
            d = value
        elif isinstance(value, bool):
            return None
        elif isinstance(value, int):
            d = Decimal(value)
        elif isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                return None
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
        self, cart_id: int, force_delete: bool = False,
    ) -> bool:
        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        items = list(cart.ordered_item or [])
        consumption_snapshot = (
            self.service.get_consumption_snapshot_for_cart(cart_id)
        )

        already_released = (
            self.cart_policy.normalize(cart.cart_status)
            in ("canceled", "cancelled", "completed", "abandoned")
        )

        deleted = self.service.cart_repo.delete_cart_by_id_sync(cart_id)

        if deleted and (items or consumption_snapshot) and not already_released:
            try:
                await self._release_inventory(items, consumption_snapshot)
            except Exception:
                logger.error(
                    "Delete succeeded but inventory release failed for "
                    "cart %s — reservations are leaked",
                    cart_id,
                )

        return deleted