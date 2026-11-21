# services/order_service.py
"""
Order service — local operations only.

Responsibilities (strictly local):
  - validations (status enums, transition legality, user/product existence)
  - model construction (PlacedOrder, OrderedItem, Delivery, Invoice)
  - persistence via repositories
  - computing totals, invoice numbers, due dates
  - entity-level rollback

NOT responsible for:
  - calling the inventory silo          → order_workflow.py
  - calling the finance service         → order_workflow.py
  - sequencing phases                   → order_workflow.py

No `inventory_client`, no `finance_client`, no `asyncio.create_task`
inside this module.
"""

import decimal
from decimal import Decimal
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from core.models.finance_models import PaymentCreate
from services.location_service import LocationService
from repositories.financial_repository import FinancialRepository
from core.models.api_models import Delivery_Info_API, OrderedItem_API, PlacedOrder_API
from core.exceptions.handler import UserNotFoundException
from core.exceptions.specific.order_exceptions import (
    OrderNotFoundException,
    OrderDeleteFailedException,
    OrderUpdateFailedException,
    InvalidOrderStatusException,
    OrderStatusTransitionException,
)
from core.exceptions.specific.product_exceptions import (
    ProductNotFoundException,
)
from core.models.models import (
    Payment,
    PlacedOrder,
    OrderedItem,
    Product,
    Invoice,
    Delivery,
)
from repositories.order_repository import OrderRepository, OrderItemRepository
from repositories.product_repository import ProductRepository
from repositories.user_repository import UserRepository
from repositories.delivery_repository import DeliveryRepository
from services.pricing_service import PricingService

from core.logging_config import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Decimal helper
# ─────────────────────────────────────────────────────────────────────

def _as_decimal(value: Any) -> Decimal:
    """
    Coerce any numeric to Decimal with a zero fallback.

    Monetary and quantity arithmetic in this module must stay in
    Decimal. Mixing float and Decimal raises `TypeError` in Python,
    and mixing int and Decimal is safe but easy to get wrong once
    the first float leaks in. This helper is the single boundary.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal("0")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except (decimal.InvalidOperation, ValueError):
            return Decimal("0")
    return Decimal("0")


def _decimal_str(value: Any) -> str:
    """For log messages only — never for arithmetic."""
    return str(_as_decimal(value))


class OrderService:
    """Local order operations. Remote orchestration lives in OrderWorkflow."""

    VALID_ORDER_STATUSES = {
        'PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED',
        'CANCELLED', 'REFUNDED',
    }

    STATUS_TRANSITIONS = {
        'PENDING':    {'PROCESSING', 'CANCELLED'},
        'PROCESSING': {'SHIPPED', 'CANCELLED'},
        'SHIPPED':    {'DELIVERED', 'CANCELLED', 'REFUNDED'},
        'DELIVERED':  {'REFUNDED'},
        'CANCELLED':  set(),
        'REFUNDED':   set(),
    }

    DEFAULT_PAGINATION_LIMIT = 100
    MAX_PAGINATION_LIMIT = 500

    def __init__(self):
        self.order_repo = OrderRepository()
        self.order_item_repo = OrderItemRepository()
        self.product_repo = ProductRepository()
        self.user_repo = UserRepository()
        self.invoice_repo = FinancialRepository()
        self.delivery_repo = DeliveryRepository()
        self.location_service = LocationService()
        self.pricing_service = PricingService()

    # ================================================================
    # LOCAL: PERSIST ENTITIES (Phase 1 core)
    # ================================================================

    def persist_order_entities(
        self,
        items: List[OrderedItem_API],
        order_data: PlacedOrder_API,
        user_id: int,
        delivery_data: Optional[Delivery_Info_API],
    ) -> Tuple[PlacedOrder, List[OrderedItem], Invoice, List[Delivery]]:
        """
        Persist order, deliveries, items, and invoice in one pass.

        Write order:
          1. Validate the ordering user.
          2. Compute totals in `Decimal` only.
          3. Persist the `PlacedOrder` (no children attached — they
             get persisted one at a time so we can set FKs).
          4. Persist one `Delivery` per distinct provider. Each
             delivery carries address, broker, provider, fee, and
             shipping method. `delivery_source_id` and
             `delivery_invoice_ref` are patched after the invoice.
          5. Persist each `OrderedItem` with `delivery_id` set to the
             delivery for its provider.
          6. Persist the `Invoice`; patch `delivery_invoice_ref` back
             onto each delivery; patch `invoice_id` back onto the order.

        Returns (order, items, invoice, deliveries).

        Pure local — no remote calls.
        """
        ordering_user = self.user_repo.get_by_id(order_data.ordering_user_id)
        if not ordering_user:
            raise UserNotFoundException(user_id=order_data.ordering_user_id)

        # ── Phase A: resolve products, accumulate totals in Decimal ──
        resolved: List[Tuple[OrderedItem_API, Product]] = []
        order_total_price: Decimal = Decimal("0")
        delivery_provider_ids: set = set()

        for api_item in items:
            product = self.product_repo.get_product_by_id(api_item.product_id)
            if not product:
                raise ProductNotFoundException(product_id=api_item.product_id)

            delivery_provider_ids.add(product.provider_id)
            resolved.append((api_item, product))

            line_price = (
                _as_decimal(api_item.ordered_quantity)
                * _as_decimal(product.unit_price)
                * (Decimal("1") + _as_decimal(api_item.vat_rate))
            )
            order_total_price += line_price

        if order_data.order_discount is not None:
            order_total_price -= _as_decimal(order_data.order_discount)

        # Delivery fee is part of the invoice total, added once per
        # delivery provider (matches the previous behaviour).
        delivery_fee_per_provider = (
            _as_decimal(delivery_data.delivery_fee)
            if delivery_data is not None else Decimal("0")
        )
        order_total_price += delivery_fee_per_provider * len(
            delivery_provider_ids
        )

        order_total_price = max(Decimal("0"), order_total_price)

        # ── Phase B: persist the order (no children) ────────────────
        placed_order = PlacedOrder(
            ordering_user_id=ordering_user.id_app_user,
            discount_amount=_as_decimal(order_data.order_discount),
            updated_at=datetime.now(),
            subtotal=order_total_price,
            order_state=self.validate_order_status(
                order_data.placed_order_state or "PENDING"
            ),
        )
        created_order = self.order_repo.create_order(placed_order)
        logger.info(
            "✅ Created order: %s (total=%s)",
            created_order.id_placed_order,
            _decimal_str(order_total_price),
        )

        # ── Phase C: resolve destination address once ───────────────
        delivery_address_id: Optional[int] = None
        if delivery_data and delivery_data.destination_address:
            if delivery_data.destination_address.id_address > 0:
                delivery_address_id = delivery_data.destination_address.id_address
            else:
                addr = self.location_service.create_address_from_location(
                    delivery_data.destination_address
                )
                if addr is None or not getattr(addr, "id_address", 0):
                    raise OrderUpdateFailedException(
                        order_id=created_order.id_placed_order,
                        error=(
                            "Could not persist destination address for "
                            "delivery"
                        ),
                        fields_attempted=["delivery"],
                    )
                delivery_address_id = addr.id_address

        # ── Phase D: persist deliveries ─────────────────────────────
        #
        # Broker defaults to 1 when the caller doesn't supply one.
        # `confirmed → shipped` requires `has_broker`, so leaving it
        # null makes the delivery unshippable. If your seed data uses
        # a different default, change this one line.
        broker_id: Optional[int] = None
        if delivery_data is not None:
            broker_id = getattr(delivery_data, "delivery_broker_id", None)
        if not broker_id:
            broker_id = 1

        deliveries: List[Delivery] = []
        delivery_by_provider: Dict[int, Delivery] = {}

        for provider_id in delivery_provider_ids:
            delivery = Delivery(
                delivery_source_type="placed_order",
                delivery_source_id=created_order.id_placed_order,
                address_id=delivery_address_id,
                # Seed tracking at the destination so `arrived_at_destination`
                # passes for the first leg if the caller drives the state
                # machine without a moving ping.
                current_address_id=delivery_address_id,
                recipient_person_id=user_id,
                delivery_provider_id=provider_id,
                delivery_broker_id=broker_id,
                delivery_fee=delivery_fee_per_provider,
                delivery_shipping_method="standard",
                delivery_status="pending",
                # `delivery_invoice_ref` is set after the invoice is
                # created (below).
            )
            created_delivery = self.delivery_repo.create(delivery)
            deliveries.append(created_delivery)
            delivery_by_provider[provider_id] = created_delivery
            logger.info(
                "✅ Created delivery: %s (provider=%s broker=%s)",
                created_delivery.id_delivery,
                provider_id,
                broker_id,
            )

        # ── Phase E: persist items with delivery_id set ─────────────
        created_items: List[OrderedItem] = []
        for api_item, product in resolved:
            item = self.build_ordered_item_model(api_item)
            item.unit_price = _as_decimal(product.unit_price)
            item.order_id = created_order.id_placed_order
            item.delivery_id = delivery_by_provider[product.provider_id].id_delivery
            saved = self.order_repo.create_order_item(item)
            created_items.append(saved)
            logger.info(
                "✅ Created order item: %s (product=%s qty=%s price=%s "
                "delivery=%s)",
                saved.id_ordered_item,
                saved.product_id,
                saved.ordered_quantity,
                _decimal_str(saved.unit_price),
                saved.delivery_id,
            )

        # ── Phase F: persist invoice and backfill refs ──────────────
        invoice = Invoice(
            invoice_reference=(
                f"INV-{created_order.id_placed_order}-"
                f"{datetime.now().strftime('%Y%m%d')}"
            ),
            grand_total=order_total_price,
            invoice_status="unpaid",
            invoice_issue_date=datetime.now().date(),
            invoice_due_date=datetime.now().date() + timedelta(days=30),
            invoice_notes=f"Order #{created_order.id_placed_order}",
            invoice_type="invoice",
            tax_amount=Decimal("0"),
        )
        created_invoice = self.invoice_repo.create_invoice(invoice)
        logger.info("✅ Created invoice: %s", created_invoice.invoice_id)

        for d in deliveries:
            d.delivery_invoice_ref = created_invoice.invoice_id
            self.delivery_repo.update(d)

        created_order.invoice_id = created_invoice.invoice_id
        created_order = self.order_repo.update_order(created_order)

        return created_order, created_items, created_invoice, deliveries

    # ================================================================
    # LOCAL: MARK INVOICE PAID / ADVANCE ORDER STATE (Phase 2 core)
    # ================================================================

    def mark_invoice_paid(self, invoice: Invoice) -> Invoice:
        """Local: flip invoice status to paid and persist."""
        invoice.invoice_status = "paid"
        return self.invoice_repo.update_invoice(invoice)

    def advance_order_after_payment(self, order: PlacedOrder) -> PlacedOrder:
        """Local: PENDING → PROCESSING after payment succeeds."""
        if order.order_state == "PENDING":
            order.order_state = "PROCESSING"
            order.updated_at = datetime.now()
            return self.order_repo.update_order(order)
        return order

    # ================================================================
    # LOCAL: BUILD PAYLOAD DICTS FOR THE WORKFLOW
    # ================================================================

    def build_payment_create_payload(
        self, order: PlacedOrder, invoice: Invoice, payment_method: str,
    ) -> PaymentCreate:
        amount = invoice.grand_total
        if amount is None:
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order,
                error=f"Invoice {invoice.invoice_id} has no total_amount",
                fields_attempted=["payment"],
            )

        user_id = order.ordering_user_id
        if user_id is None:
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order,
                error="Order has no ordering_user_id",
                fields_attempted=["payment"],
            )

        return PaymentCreate(
            invoice_id=invoice.invoice_id,
            amount=_as_decimal(amount),
            payment_method=payment_method,
            user_id=int(user_id),
            notes=f"Order #{order.id_placed_order} payment",
            payment_type="payment",
        )

    def build_payment_transaction_details(
        self,
        order: PlacedOrder,
        invoice: Invoice,
        payment_method: str,
    ) -> Dict[str, Any]:
        return {
            "reference": (
                f"ORD-{order.id_placed_order}-"
                f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ),
            "order_id": order.id_placed_order,
            "invoice_id": invoice.invoice_id,
            "payment_method": payment_method,
            "notes": f"Payment for order #{order.id_placed_order}",
        }

    def build_reserve_payload(
        self, items: List[OrderedItem],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "id": item.id_ordered_item,
                "quantity": int(item.ordered_quantity or 0),
                "product_id": item.product_id,
            }
            for item in items
        ]

    def build_confirm_payload(
        self, items: List[Any],
    ) -> List[Dict[str, Any]]:
        confirm_items: List[Dict[str, Any]] = []
        for item in items:
            normalized = self.normalize_confirm_item(item)
            if normalized is not None:
                confirm_items.append(normalized)
        return confirm_items

    @staticmethod
    def normalize_confirm_item(item: Any) -> Optional[Dict[str, Any]]:
        if isinstance(item, dict):
            ordered_item_id = item.get("id_ordered_item") or item.get("id")
            quantity = item.get("ordered_quantity")
            product_id = item.get("product_id")
        else:
            ordered_item_id = getattr(item, "id_ordered_item", None)
            quantity = getattr(item, "ordered_quantity", None)
            product_id = getattr(item, "product_id", None)

        if ordered_item_id is None or product_id is None:
            logger.warning("Skipping malformed confirm item: %r", item)
            return None

        return {
            "id": ordered_item_id,
            "quantity": int(quantity or 0),
            "product_id": product_id,
        }

    def parse_inventory_response(self, response: Dict) -> Dict:
        if not response:
            return {}

        result: Dict = {}

        if all(isinstance(v, dict) for v in response.values()):
            return response

        for key in ("items", "data", "results"):
            if key in response and isinstance(response[key], list):
                for item in response[key]:
                    pid = item.get("product_id")
                    if pid:
                        result[str(pid)] = item
                return result

        for key, value in response.items():
            try:
                int(key)
                result[str(key)] = value
            except (ValueError, TypeError):
                pass

        return result

    # ================================================================
    # LOCAL: ROLLBACK
    # ================================================================

    def rollback_entities(
        self,
        order: Optional[PlacedOrder],
        invoice: Optional[Invoice],
        items: List[OrderedItem],
        deliveries: List[Delivery],
    ) -> None:
        """
        Local: delete whatever was created, in reverse dependency order.

        Order is now:
          1. Order items (FK to delivery and order; delete first).
          2. Deliveries (FK to invoice via `delivery_invoice_ref`).
          3. Invoice.
          4. Order.

        Remote release of inventory is the workflow's job. This method
        refuses to delete anything that still has an active reservation
        so the phantom-reservation failure mode is impossible.
        """
        logger.info("🔄 Rolling back order entities...")

        # Guard: refuse to remove items whose stock is still on hold.
        stuck = [
            i for i in (items or [])
            if int(getattr(i, "reserved_quantity", 0) or 0) > 0
        ]
        if stuck:
            ids = ", ".join(str(getattr(i, "id_ordered_item", "?")) for i in stuck)
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order if order else 0,
                error=(
                    f"Cannot roll back: ordered items {ids} still hold "
                    f"reserved stock; release inventory first"
                ),
                fields_attempted=["rollback"],
            )

        # 1. Items first.
        if items:
            try:
                for item in items:
                    self.order_repo.delete_order_item(item)
                logger.info("✅ Order items deleted")
            except Exception as e:
                logger.error("Failed to delete order items: %s", e)

        # 2. Deliveries.
        for d in deliveries or []:
            try:
                self.delivery_repo.delete(d)
                logger.info(
                    "✅ Delivery %s deleted",
                    getattr(d, "id_delivery", "?"),
                )
            except Exception as e:
                logger.error(
                    "Failed to delete delivery %s: %s",
                    getattr(d, "id_delivery", "?"), e,
                )

        # 3. Invoice.
        if invoice:
            try:
                self.invoice_repo.delete_invoice(invoice)
                logger.info("✅ Invoice deleted")
            except Exception as e:
                logger.error("Failed to delete invoice: %s", e)

        # 4. Order.
        if order:
            try:
                basic = self.order_repo.get_order_basic(
                    order.id_placed_order
                )
                if basic is not None:
                    self.order_repo.delete_order(basic)
                    logger.info("✅ Order deleted")
            except Exception as e:
                logger.error("Failed to delete order: %s", e)

        logger.info("✅ Entity rollback completed")

    # ================================================================
    # LOCAL: PUBLIC READ / WRITE
    # ================================================================

    def update_order_status(
        self, order_id: int, new_status: str,
    ) -> PlacedOrder:
        validated = self.validate_order_status(new_status)
        order = self.get_order_by_id(order_id, with_items=False)
        self.validate_status_transition(order.order_state, validated)

        order.order_state = validated
        order.updated_at = datetime.now()
        return self.order_repo.update_order(order)

    def delete_order(self, order_id: int) -> bool:
        """Local-only delete. Workflow releases inventory first."""
        logger.info("Deleting order with ID: %s", order_id)
        self.get_order_by_id(order_id, with_items=True)

        try:
            self.order_item_repo.bulk_delete_by_order(order_id)
            basic_order = self.order_repo.get_order_basic(order_id)
            if basic_order:
                result = self.order_repo.delete_order(basic_order)
                logger.info("Order %s deleted successfully", order_id)
                return result
            return False
        except Exception as e:
            logger.error("Failed to delete order %s: %s", order_id, e)
            raise OrderDeleteFailedException(order_id=order_id, error=str(e))

    def build_ordered_item_model(
        self, api_item: OrderedItem_API,
    ) -> OrderedItem:
        item = OrderedItem(
            product_id=api_item.product_id,
            ordered_quantity=api_item.ordered_quantity,
            vat_rate=_as_decimal(api_item.vat_rate),
            unit_price=_as_decimal(api_item.unit_price),
            delivery_id=getattr(api_item, "delivery_id", None),
        )
        if getattr(api_item, "order_id", None) and api_item.order_id > 0:
            item.order_id = api_item.order_id
        return item

    def validate_order_status(self, status: str) -> str:
        if not status:
            return "PENDING"
        normalized = status.upper()
        if normalized not in self.VALID_ORDER_STATUSES:
            logger.warning("Invalid order status: %s", status)
            raise InvalidOrderStatusException(
                status=status,
                valid_statuses=list(self.VALID_ORDER_STATUSES),
            )
        return normalized

    def validate_status_transition(
        self, current_status: str, new_status: str,
    ) -> None:
        if new_status == current_status:
            return
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            logger.warning(
                "Invalid status transition from %s to %s",
                current_status, new_status,
            )
            raise OrderStatusTransitionException(
                current_status=current_status,
                new_status=new_status,
                allowed_transitions=list(allowed),
            )

    def get_order_by_id(
        self, order_id: int, with_items: bool = True,
    ) -> PlacedOrder:
        if with_items:
            order = self.order_repo.get_order_by_id(order_id)
        else:
            order = self.order_repo.get_order_basic(order_id)
        if not order:
            raise OrderNotFoundException(order_id=order_id)
        return order

    def get_user_orders(
        self, user_id: int, offset: int = 0, limit: int = 100,
    ) -> List[PlacedOrder]:
        return self.order_repo.get_user_orders(user_id, offset, limit)

    def get_order_items(self, order_id: int) -> List[OrderedItem]:
        return self.order_item_repo.get_by_order(order_id)

    def update_order(
        self,
        order_id: int,
        items: List[OrderedItem_API],
        order_data: PlacedOrder_API,
    ) -> Dict:
        logger.info("Updating order %s", order_id)
        existing_order = self.get_order_by_id(order_id, with_items=True)

        if order_data.placed_order_state:
            validated = self.validate_order_status(
                order_data.placed_order_state
            )
            self.validate_status_transition(
                existing_order.order_state, validated
            )
            existing_order.order_state = validated

        if order_data.order_discount is not None:
            existing_order.discount_amount = _as_decimal(
                order_data.order_discount
            )

        existing_order.updated_at = datetime.now()
        updated_order = self.order_repo.update_order(existing_order)

        if items:
            self.order_item_repo.bulk_delete_by_order(order_id)
            new_items: List[OrderedItem] = []
            for api_item in items:
                item = self.build_ordered_item_model(api_item)
                item.order_id = order_id
                new_items.append(item)
            self.order_item_repo.bulk_create(new_items)

        return {
            "order": updated_order,
            "items_updated": len(items) if items else 0,
        }

    # ================================================================
    # LOCAL: INVOICE LOOKUP (used by workflow)
    # ================================================================

    def get_invoice_for_order(self, order: PlacedOrder) -> Invoice:
        if not order.invoice_id:
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order,
                error="Order has no linked invoice",
                fields_attempted=["payment"],
            )
        invoice = self.invoice_repo.get_invoice_by_id(order.invoice_id)
        if not invoice:
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order,
                error=f"Invoice {order.invoice_id} not found",
                fields_attempted=["payment"],
            )
        return invoice

    def get_completed_payment_for_invoice(
        self, invoice_id: int,
    ) -> Optional[Payment]:
        """Idempotency guard for process_payment retries."""
        return self.invoice_repo.get_by_invoice_id_and_status(
            invoice_id=invoice_id,
            statuses=("completed", "confirmed", "paid"),
        )