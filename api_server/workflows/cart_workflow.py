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
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from storage.wrappers.inventory_client import InventoryServiceClient
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
        """
        Phase 1 orchestration:
          1. local: validate entities
          2. local: load catalog
          3. local: build reservation plan
          4. remote: check inventory availability
          5. local: build cart
          6. local: persist cart + invoice
          7. remote: reserve inventory
          8. remote + local: process payment IF intent declared
          9. remote: confirm reservations
         10. on failure at any remote step: rollback local + release remote
        """
        logger.info(
            f"Creating cart for provider {provider_id}, "
            f"seller {seller_user_id}"
        )

        if not ordered_items and not ordered_services:
            from core.exceptions.specific.cart_exceptions import (
                CartCreationFailedException,
            )
            raise CartCreationFailedException(
                error="Cart must have at least one item or service",
                provider_id=provider_id,
                seller_id=seller_user_id,
            )

        intent = self.service.detect_payment_intent(cart_data)
        logger.info(f"Detected payment intent: {intent.value}")

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
            # Single canonical path: process_payment. Idempotent, so a
            # later finalize_cart will not create a duplicate.
            financial_docs: Dict[str, Any] = {}
            if intent in (PaymentIntent.FULL, PaymentIntent.DEPOSIT):
                logger.info(
                    "Step 8: Processing payment via process_payment..."
                )
                financial_docs = await self.process_payment(
                    cart_id=created_cart.cart_id,
                    payment_method=(
                        getattr(cart_data, "cart_payment_method", None)
                        or "cash"
                    ),
                    captured_amount=self.service.safe_float(
                        getattr(cart_data, "cart_paid_money", 0)
                    ) or None,
                )
            else:
                logger.info(
                    f"Step 8: No payment requested (intent={intent.value})"
                )

            # Step 9 — remote: confirm reservations
            logger.info("Step 9: Confirming reservations...")
            await self._confirm_reservations(
                created_items, created_services, reservation_plan
            )

            financial_docs["invoice"] = created_invoice

            logger.info(f"Cart {created_cart.cart_id} creation completed")
            return financial_docs, created_cart

        except Exception as e:
            logger.error(f"Cart creation failed: {e}")

            if inventory_reserved:
                await self._safe_release_inventory(
                    created_items,
                    [
                        c
                        for svc in created_services
                        for c in (svc.product_consumption or [])
                    ],
                )

            await self.service.rollback_cart_creation(
                created_cart, created_items
            )
            raise

    # ================================================================
    # PHASE 2 — PROCESS PAYMENT
    # ================================================================

    async def process_payment(
        self,
        cart_id: int,
        payment_method: str = 'card',
        captured_amount: Optional[float] = None,
        transaction_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Processing payment for cart {cart_id}...")

        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        invoice = self.service.get_invoice_for_cart(cart)

        # Guard 1: invoice already paid
        current_status = self.invoice_policy.normalize(
            invoice.invoice_status or 'unpaid'
        )
        if current_status == 'paid':
            logger.info(f"Cart {cart_id} invoice already paid — skipping")
            return {
                'cart_id': cart_id,
                'invoice_id': invoice.invoice_id,
                'payment_id': None,
                'payment_status': 'paid',
            }

        # Guard 2: existing completed payment for this invoice
        existing = self.service.get_completed_payment_for_invoice(
            invoice.invoice_id
        )
        if existing:
            logger.info(
                f"Invoice {invoice.invoice_id} already has completed "
                f"payment {existing.payment_id} — skipping"
            )
            return {
                'cart_id': cart_id,
                'invoice_id': invoice.invoice_id,
                'payment_id': existing.payment_id,
                'payment_status': existing.payment_status,
            }

        # Decide which target state the invoice should reach.
        if captured_amount is None:
            target = 'paid'
            extras = {'captured_amount': None}
        else:
            total = float(invoice.invoice_total_amount or 0)
            target = 'paid' if captured_amount >= total else 'partially_paid'
            extras = {'captured_amount': captured_amount}

        invoice_decision = self.invoice_policy.decide_for_invoice(
            invoice, target=target, **extras
        )
        if not invoice_decision.allowed:
            raise ValueError(
                f"Invoice transition denied: {invoice_decision.reason}"
            )

        # Remote: create payment
        amount = (
            captured_amount
            if captured_amount is not None
            else float(invoice.invoice_total_amount or 0)
        )
        payment_payload = self.service.build_payment_create_payload(
            cart=cart,
            invoice=invoice,
            payment_method=payment_method,
            captured_amount=amount,
        )
        payment_response = await self.finance_client.create_payment(
            payment_payload
        )
        logger.info(f"✅ Payment created: {payment_response.id}")

        # Remote: confirm payment
        details = (
            transaction_details
            or self.service.build_payment_transaction_details(
                cart=cart,
                invoice=invoice,
                payment_method=payment_method,
            )
        )
        confirmed_payment = await self.finance_client.confirm_payment(
            payment_id=payment_response.id,
            transaction_details=details,
        )
        logger.info(
            f"✅ Payment {confirmed_payment.id} confirmed "
            f"(status={confirmed_payment.status})"
        )


        # Local: apply the invoice decision
        self.service.apply_invoice_status(invoice, invoice_decision.target)

        logger.info(
            f"Applied transition: invoice "
            f"{invoice_decision.current} → {invoice_decision.target}"
        )

        return {
            'cart_id': cart.cart_id,
            'invoice_id': invoice.invoice_id,
            'payment_id': confirmed_payment.id,
            'payment_status': confirmed_payment.status,
        }

    # ================================================================
    # PHASE 3 — CONFIRM INVENTORY
    # ================================================================

    async def confirm_inventory_for_cart(
        self, cart_id: int
    ) -> Dict[str, Any]:
        """Phase 3 orchestration (by cart id)."""
        logger.info(f"Confirming inventory for cart {cart_id}...")

        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        items = list(cart.ordered_item or [])
        services = list(cart.ordered_service or [])

        if not items and not services:
            logger.info(f"Cart {cart_id} has no items to confirm")
            return {
                'cart_id': cart_id,
                'items_confirmed': 0,
                'success': True,
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
            logger.info(f"No items to confirm for cart {cart_id}")
            return {
                'cart_id': cart_id,
                'items_confirmed': 0,
                'success': True,
            }

        await self.inventory_client.bulk_confirm(
            ordered_payload,
            consumption_payload,
        )

        total = len(ordered_payload) + len(consumption_payload)
        logger.info(
            f"✅ Inventory confirmed ({total} entries) for cart {cart_id}"
        )
        return {
            'cart_id': cart_id,
            'items_confirmed': total,
            'success': True,
        }

    # ================================================================
    # EXPLICIT CART TRANSITIONS (policy-gated)
    # ================================================================

    async def mark_cart_pending(self, cart_id: int) -> Dict[str, Any]:
        """open → pending, gated by CartPolicy."""
        return self._transition_cart(cart_id, target='pending')

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
            target='checkout',
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
            target='completed',
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
            target='partial',
            partially_fulfilled=partially_fulfilled,
        )

    async def mark_cart_abandoned(
        self,
        cart_id: int,
        *,
        stale: bool = True,
    ) -> Dict[str, Any]:
        """open → abandoned, gated by CartPolicy."""
        return self._transition_cart(
            cart_id,
            target='abandoned',
            stale=stale,
        )

    async def reopen_cart(self, cart_id: int) -> Dict[str, Any]:
        """abandoned → open, gated by CartPolicy."""
        return self._transition_cart(cart_id, target='open')

    async def cancel_cart(
        self,
        cart_id: int,
        *,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """* → canceled, gated by CartPolicy."""
        cart = self.service.get_cart_by_id(cart_id, eager_load=True)

        decision = self.cart_policy.decide_for_cart(cart, target='canceled')
        if not decision.allowed:
            raise ValueError(f"Cart transition denied: {decision.reason}")

        items = list(cart.ordered_item or [])
        services = list(cart.ordered_service or [])
        consumptions = [
            c for svc in services for c in (svc.product_consumption or [])
        ]
        if items or consumptions:
            await self._safe_release_inventory(items, consumptions)

        result = self._apply_cart_decision(cart, decision)
        result['reason'] = reason
        return result

    # ================================================================
    # EXPLICIT ITEM / SERVICE TRANSITIONS (policy-gated)
    # ================================================================

    async def mark_item_shipped(self, item_id: int) -> Dict[str, Any]:
        """processing → shipped, gated by OrderedItemPolicy."""
        item = self.service.get_ordered_item(item_id)

        decision = self.item_policy.decide_for_item(
            item, target='shipped', delivery_confirmed=True
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
            extras['scheduled_at'] = scheduled_at
            service.ordered_service_scheduled_at = scheduled_at

        decision = self.service_policy.decide_for_service(
            service, target='scheduled', **extras
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
        payment_method: str = 'card',
        captured_amount: Optional[float] = None,
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
            'inventory_deducted': True,
        }

    # ================================================================
    # INTERNAL — cart transition core
    # ================================================================

    def _transition_cart(
        self,
        cart_id: int,
        target: str,
        **extras: Any,
    ) -> Dict[str, Any]:
        """Shared core for every `mark_cart_*` method."""
        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        decision = self.cart_policy.decide_for_cart(
            cart, target=target, **extras
        )
        if not decision.allowed:
            raise ValueError(f"Cart transition denied: {decision.reason}")
        return self._apply_cart_decision(cart, decision)

    def _apply_cart_decision(
        self, cart: Cart, decision
    ) -> Dict[str, Any]:
        """Local: persist the cart's new status per a policy decision."""
        cart.cart_status = decision.target
        cart.cart_updated_at = datetime.now()
        self.service.cart_repo.update_cart(cart)

        logger.info(
            f"Cart {cart.cart_id}: {decision.current} → {decision.target} "
            f"(side effects: {decision.side_effects})"
        )
        return {
            'cart_id': cart.cart_id,
            'previous_status': decision.current,
            'new_status': decision.target,
            'side_effects': decision.side_effects,
        }

    @staticmethod
    def _decision_to_dict(entity_id: int, decision) -> Dict[str, Any]:
        return {
            'entity_id': entity_id,
            'previous_status': decision.current,
            'new_status': decision.target,
            'side_effects': decision.side_effects,
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

        from core.exceptions.handler import InsufficientStockException

        for product_id, plan in reservation_plan.items():
            stock_data = stock_by_product.get(str(product_id), {})
            available_qty = stock_data.get("available_quantity", 0)
            requested_qty = plan["quantity"]
            if available_qty < requested_qty:
                raise InsufficientStockException(
                    product_id=product_id,
                    requested=requested_qty,
                    available=available_qty,
                )

        logger.info("✅ Inventory availability check passed")

    async def _reserve_inventory(
        self,
        reservation_plan: Dict[int, Dict],
        created_items: List[OrderedItem],
        created_services: List[OrderedService],
    ) -> None:
        """Remote: reserve inventory for persisted items + consumptions."""
        if not reservation_plan:
            logger.info("No items to reserve")
            return

        ordered_reserve_items: List[Dict[str, Any]] = []
        for item in created_items:
            if item.ordered_quantity and item.ordered_quantity > 0:
                ordered_reserve_items.append({
                    "id": item.id_ordered_item,
                    "quantity": item.ordered_quantity,
                    "item_type": "ordered_item",
                })

        consumption_reserve_items: List[Dict[str, Any]] = []
        for service in created_services:
            for consumption in service.product_consumption or []:
                pid = consumption.consumed_product_id
                qty = 0
                plan = reservation_plan.get(pid, {})
                for source in plan.get("sources", []):
                    if (
                        source.get("type") == "consumption"
                        and source.get("id") == consumption.resource_req_ref
                    ):
                        qty = source.get("quantity", 0)
                        break
                if qty and qty > 0:
                    consumption_reserve_items.append({
                        "id": consumption.id_product_consumption,
                        "quantity": qty,
                        "item_type": "consumption",
                    })

        if ordered_reserve_items:
            await self.inventory_client.reserve_inventory(
                items=ordered_reserve_items,
                item_type="ordered_item",
            )
            logger.info(
                f"✅ Reserved {len(ordered_reserve_items)} ordered items"
            )

        if consumption_reserve_items:
            try:
                await self.inventory_client.reserve_inventory(
                    items=consumption_reserve_items,
                    item_type="consumption",
                )
                logger.info(
                    f"✅ Reserved {len(consumption_reserve_items)} consumptions"
                )
            except Exception:
                if ordered_reserve_items:
                    try:
                        await self.inventory_client.release_inventory(
                            items=ordered_reserve_items,
                            item_type="ordered_item",
                        )
                    except Exception as release_error:
                        logger.error(
                            f"Failed to release ordered items: "
                            f"{release_error}"
                        )
                raise

    async def _handle_payment(
        self,
        intent: PaymentIntent,
        cart: Cart,
        invoice: Invoice,
        total_price: float,
        cart_data: Cart_API,
    ) -> Dict[str, Any]:
        """
        DEPRECATED — kept for backward compatibility only.

        Payment is now handled exclusively by process_payment / finalize_cart.
        Retained so external callers do not break; it always defers to
        process_payment.
        """
        logger.warning(
            "_handle_payment called directly; deferring to process_payment. "
            "This method is deprecated."
        )
        return await self.process_payment(
            cart_id=cart.cart_id,
            payment_method=(
                getattr(cart_data, "cart_payment_method", None) or "cash"
            ),
            captured_amount=self.service.safe_float(
                getattr(cart_data, "cart_paid_money", 0)
            ) or None,
        )

    async def _confirm_reservations(
        self,
        created_items: List[OrderedItem],
        created_services: List[OrderedService],
        reservation_plan: Dict[int, Dict],
    ) -> None:
        """Remote: confirm the reservations that were just created."""
        ordered_payload: List[Dict[str, Any]] = [
            {"id": item.id_ordered_item, "quantity": item.ordered_quantity}
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
                        and source.get("id") == consumption.resource_req_ref
                    ):
                        qty = source.get("quantity", 0)
                        if qty and qty > 0:
                            consumption_payload.append({
                                "id": consumption.id_product_consumption,
                                "quantity": qty,
                            })
                        break

        await self.inventory_client.bulk_confirm(
            ordered_payload,
            consumption_payload,
        )

    async def _safe_release_inventory(
        self,
        items: List[Any],
        consumptions: List[Any],
    ) -> None:
        """Remote: best-effort release. Never raises."""
        try:
            ordered_release: List[Dict[str, Any]] = []
            for item in items or []:
                iid = getattr(item, 'id_ordered_item', None) or (
                    item.get('id') if isinstance(item, dict) else None
                )
                qty = getattr(item, 'ordered_quantity', None) or (
                    item.get('quantity') if isinstance(item, dict) else None
                )
                pid = getattr(item, 'ordered_product_id', None) or (
                    item.get('product_id') if isinstance(item, dict) else None
                )
                if iid:
                    ordered_release.append({
                        "id": iid,
                        "quantity": qty,
                        "product_id": pid,
                    })

            if ordered_release:
                await self.inventory_client.release_inventory(
                    items=ordered_release,
                    item_type="ordered_item",
                )

            consumption_release: List[Dict[str, Any]] = []
            for c in consumptions or []:
                cid = getattr(c, 'id_product_consumption', None) or (
                    c.get('id') if isinstance(c, dict) else None
                )
                qty = getattr(c, 'product_reserved_quantity', 0) or (
                    c.get('quantity', 0) if isinstance(c, dict) else 0
                )
                if cid:
                    consumption_release.append({
                        "id": cid,
                        "quantity": qty,
                    })

            if consumption_release:
                await self.inventory_client.release_inventory(
                    items=consumption_release,
                    item_type="consumption",
                )

            logger.info("✅ Inventory released")
        except Exception as e:
            logger.error(f"Failed to release inventory: {e}")

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
                iid = item.get('id') or item.get('id_ordered_item')
                qty = item.get('quantity') or item.get('ordered_quantity')
            else:
                iid = getattr(item, 'id_ordered_item', None)
                qty = getattr(item, 'ordered_quantity', None)
            if iid and qty and qty > 0:
                payload.append({'id': iid, 'quantity': qty})
        return payload

    @staticmethod
    def _build_confirm_consumption_payload(
        services: List[Any],
    ) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for service in services or []:
            if isinstance(service, dict):
                consumptions = service.get('product_consumption', []) or []
            else:
                consumptions = getattr(service, 'product_consumption', None) or []
            for c in consumptions:
                if isinstance(c, dict):
                    cid = c.get('id') or c.get('id_product_consumption')
                    qty = (
                        c.get('quantity')
                        or c.get('product_reserved_quantity', 0)
                    )
                else:
                    cid = getattr(c, 'id_product_consumption', None)
                    qty = getattr(c, 'product_reserved_quantity', 0)
                if cid and qty and qty > 0:
                    payload.append({'id': cid, 'quantity': qty})
        return payload

    # ================================================================
    # DELETE CART
    # ================================================================

    async def delete_cart(
        self, cart_id: int, force_delete: bool = False
    ) -> bool:
        """Orchestrates: release remote inventory → delete local."""
        logger.info(f"Deleting cart {cart_id} (force={force_delete})")

        cart = self.service.get_cart_by_id(cart_id, eager_load=True)
        items = list(cart.ordered_item or [])
        services = list(cart.ordered_service or [])
        consumptions = [
            c for svc in services for c in (svc.product_consumption or [])
        ]

        if items or consumptions:
            await self._safe_release_inventory(items, consumptions)

        return self.service.cart_repo.delete_cart_by_id_sync(cart_id)