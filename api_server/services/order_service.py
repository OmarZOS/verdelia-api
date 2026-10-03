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
from core.models.models import PlacedOrder, OrderedItem, Product, Invoice, Delivery
from repositories.order_repository import OrderRepository, OrderItemRepository
from repositories.product_repository import ProductRepository
from repositories.user_repository import UserRepository
from repositories.delivery_repository import DeliveryRepository
from services.pricing_service import PricingService

from core.logging_config import get_logger

logger = get_logger(__name__)



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
        Persist order, items, deliveries, and invoice in one pass.
        Pure local — no remote calls.

        Returns (order, items, invoice, deliveries).
        """
        ordering_user = self.user_repo.get_by_id(order_data.ordering_user_id)
        if not ordering_user:
            raise UserNotFoundException(user_id=order_data.ordering_user_id)

        ordered_items: List[OrderedItem] = []
        order_total_price: float = 0.0
        delivery_provider_ids: set = set()

        for api_item in items:
            product = self.product_repo.get_product_by_id(
                api_item.ordered_product_id
            )
            if not product:
                raise ProductNotFoundException(
                    product_id=api_item.ordered_product_id
                )

            delivery_provider_ids.add(product.product_provider_id)

            item = self.build_ordered_item_model(api_item)
            item.unit_price = float(product.product_price)
            ordered_items.append(item)

            order_total_price += (
                item.ordered_quantity
                * float(product.product_price)
                * (1 + item.applied_vat)
            )

        if order_data.order_discount:
            order_total_price -= order_data.order_discount
        order_total_price = round(max(0, order_total_price), 2)

        placed_order = PlacedOrder(
            ordering_user_id=ordering_user.id_app_user,
            order_discount=order_data.order_discount or 0,
            placed_order_last_mod=datetime.now(),
            total_price=max(0, order_total_price),
            placed_order_state=self.validate_order_status(
                order_data.placed_order_state or 'PENDING'
            ),
        )
        placed_order.ordered_item = ordered_items

        created_order = self.order_repo.create_order(placed_order)
        logger.info(f"✅ Created order: {created_order.id_placed_order}")

        created_items: List[OrderedItem] = []
        for item in ordered_items:
            item.order_ref = created_order.id_placed_order
            saved = self.order_repo.create_order_item(item)
            created_items.append(saved)
            logger.info(
                f"✅ Created order item: {saved.id_ordered_item} "
                f"for product {saved.ordered_product_id}"
            )

        deliveries: List[Delivery] = []
        for provider_id in delivery_provider_ids:
            delivery_address_id: Optional[int] = None

            if delivery_data and delivery_data.destination_address:
                if delivery_data.destination_address.id_address > 0:
                    delivery_address_id = (
                        delivery_data.destination_address.id_address
                    )
                else:
                    addr = self.location_service.create_address_from_location(
                        delivery_data.destination_address
                    )
                    delivery_address_id = addr.id_address

            delivery = Delivery(
                delivery_source_type='placed_order',
                delivery_address_id=delivery_address_id,
                recipient_person=user_id,
                delivery_source_id=created_order.id_placed_order,
                delivery_provider_id=provider_id,
                delivery_fee=(
                    delivery_data.delivery_fee if delivery_data else 0.0
                ),
            )
            deliveries.append(delivery)
            order_total_price += (
                delivery_data.delivery_fee if delivery_data else 0.0
            )

        invoice = Invoice(
            invoice_number=(
                f"INV-{created_order.id_placed_order}-"
                f"{datetime.now().strftime('%Y%m%d')}"
            ),
            invoice_total_amount=order_total_price,
            invoice_status='unpaid',
            invoice_issue_date=datetime.now().date(),
            invoice_due_date=datetime.now().date() + timedelta(days=30),
            invoice_notes=f"Order #{created_order.id_placed_order}",
            invoice_type='invoice',
            invoice_tax_applied=19,
            delivery=deliveries,
        )
        created_invoice = self.invoice_repo.create_invoice(invoice)
        logger.info(f"✅ Created invoice: {created_invoice.invoice_id}")

        created_order.placed_order_invoice = created_invoice.invoice_id
        created_order = self.order_repo.update_order(created_order)

        return created_order, created_items, created_invoice, deliveries

    # ================================================================
    # LOCAL: MARK INVOICE PAID / ADVANCE ORDER STATE (Phase 2 core)
    # ================================================================

    def mark_invoice_paid(self, invoice: Invoice) -> Invoice:
        """Local: flip invoice status to paid and persist."""
        invoice.invoice_status = 'paid'
        return self.invoice_repo.update_invoice(invoice)

    def advance_order_after_payment(self, order: PlacedOrder) -> PlacedOrder:
        """Local: PENDING → PROCESSING after payment succeeds."""
        if order.placed_order_state == 'PENDING':
            order.placed_order_state = 'PROCESSING'
            order.placed_order_last_mod = datetime.now()
            return self.order_repo.update_order(order)
        return order

    # ================================================================
    # LOCAL: BUILD PAYLOAD DICTS FOR THE WORKFLOW
    # ================================================================

    def build_payment_create_payload(self, order, invoice, payment_method):
        amount = invoice.invoice_total_amount
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
            invoice_id= invoice.invoice_id,
            amount= float(amount),
            payment_method= payment_method,
            user_id= int(user_id),
            notes= f"Order #{order.id_placed_order} payment",
            payment_type= 'payment',)
        

    def build_payment_transaction_details(
        self,
        order: PlacedOrder,
        invoice: Invoice,
        payment_method: str,
    ) -> Dict[str, Any]:
        return {
            'reference': (
                f'ORD-{order.id_placed_order}-'
                f'{datetime.now().strftime("%Y%m%d%H%M%S")}'
            ),
            'order_id': order.id_placed_order,
            'invoice_id': invoice.invoice_id,
            'payment_method': payment_method,
            'notes': f'Payment for order #{order.id_placed_order}',
        }

    def build_reserve_payload(
        self, items: List[OrderedItem]
    ) -> List[Dict[str, Any]]:
        return [
            {
                'id': item.id_ordered_item,
                'quantity': item.ordered_quantity,
                'product_id': item.ordered_product_id,
            }
            for item in items
        ]

    def build_confirm_payload(
        self, items: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Local: normalize items into the shape the silo expects.
        Accepts ORM objects or dicts; skips malformed rows.
        """
        confirm_items: List[Dict[str, Any]] = []
        for item in items:
            normalized = self.normalize_confirm_item(item)
            if normalized is not None:
                confirm_items.append(normalized)
        return confirm_items

    @staticmethod
    def normalize_confirm_item(item: Any) -> Optional[Dict[str, Any]]:
        if isinstance(item, dict):
            ordered_item_id = item.get('id_ordered_item')
            quantity = item.get('ordered_quantity')
            product_id = item.get('ordered_product_id')
        else:
            ordered_item_id = getattr(item, 'id_ordered_item', None)
            quantity = getattr(item, 'ordered_quantity', None)
            product_id = getattr(item, 'ordered_product_id', None)

        if ordered_item_id is None or product_id is None:
            logger.warning(f"Skipping malformed confirm item: {item!r}")
            return None

        return {
            'id': ordered_item_id,
            'quantity': quantity,
            'product_id': product_id,
        }

    def parse_inventory_response(self, response: Dict) -> Dict:
        """Local: normalize the silo's bulk-stock response shape."""
        if not response:
            return {}

        result = {}

        if all(isinstance(v, dict) for v in response.values()):
            return response

        for key in ('items', 'data', 'results'):
            if key in response and isinstance(response[key], list):
                for item in response[key]:
                    pid = item.get('product_id')
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
        Remote release of inventory is the workflow's job.
        """
        logger.info("🔄 Rolling back order entities...")

        for d in deliveries:
            try:
                self.delivery_repo.delete(d)
            except Exception as e:
                logger.error(f"Failed to delete delivery: {e}")

        if invoice:
            try:
                self.invoice_repo.delete_invoice(invoice)
                logger.info("✅ Invoice deleted")
            except Exception as e:
                logger.error(f"Failed to delete invoice: {e}")

        if items:
            try:
                for item in items:
                    self.order_repo.delete_order_item(item)
                logger.info("✅ Order items deleted")
            except Exception as e:
                logger.error(f"Failed to delete order items: {e}")

        if order:
            try:
                self.order_repo.delete_order(order)
                logger.info("✅ Order deleted")
            except Exception as e:
                logger.error(f"Failed to delete order: {e}")

        logger.info("✅ Entity rollback completed")

    # ================================================================
    # LOCAL: PUBLIC READ / WRITE (unchanged)
    # ================================================================

    def update_order_status(self, order_id: int, new_status: str) -> PlacedOrder:
        validated = self.validate_order_status(new_status)
        order = self.get_order_by_id(order_id, with_items=False)
        self.validate_status_transition(order.placed_order_state, validated)

        order.placed_order_state = validated
        order.placed_order_last_mod = datetime.now()
        return self.order_repo.update_order(order)

    def delete_order(self, order_id: int) -> bool:
        """Local-only delete. Workflow is responsible for releasing inventory."""
        logger.info(f"Deleting order with ID: {order_id}")
        order = self.get_order_by_id(order_id, with_items=True)

        try:
            self.order_item_repo.bulk_delete_by_order(order_id)
            basic_order = self.order_repo.get_order_basic(order_id)
            if basic_order:
                result = self.order_repo.delete_order(basic_order)
                logger.info(f"Order {order_id} deleted successfully")
                return result
            return False
        except Exception as e:
            logger.error(f"Failed to delete order {order_id}: {e}")
            raise OrderDeleteFailedException(order_id=order_id, error=str(e))

    def build_ordered_item_model(
        self, api_item: OrderedItem_API
    ) -> OrderedItem:
        item = OrderedItem(
            ordered_product_id=api_item.ordered_product_id,
            ordered_quantity=api_item.ordered_quantity,
            applied_vat=api_item.applied_vat,
            unit_price=api_item.unit_price,
        )
        if api_item.order_ref and api_item.order_ref > 0:
            item.order_ref = api_item.order_ref
        return item

    def validate_order_status(self, status: str) -> str:
        if not status:
            return 'PENDING'
        normalized = status.upper()
        if normalized not in self.VALID_ORDER_STATUSES:
            logger.warning(f"Invalid order status: {status}")
            raise InvalidOrderStatusException(
                status=status,
                valid_statuses=list(self.VALID_ORDER_STATUSES),
            )
        return normalized

    def validate_status_transition(
        self, current_status: str, new_status: str
    ) -> None:
        if new_status == current_status:
            return
        allowed = self.STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            logger.warning(
                f"Invalid status transition from {current_status} "
                f"to {new_status}"
            )
            raise OrderStatusTransitionException(
                current_status=current_status,
                new_status=new_status,
                allowed_transitions=list(allowed),
            )

    def get_order_by_id(
        self, order_id: int, with_items: bool = True
    ) -> PlacedOrder:
        if with_items:
            order = self.order_repo.get_order_by_id(order_id)
        else:
            order = self.order_repo.get_order_basic(order_id)
        if not order:
            raise OrderNotFoundException(order_id=order_id)
        return order

    def get_user_orders(
        self, user_id: int, offset: int = 0, limit: int = 100
    ):
        return self.order_repo.get_orders_by_user(user_id, offset, limit)

    def get_order_items(self, order_id: int) -> List[OrderedItem]:
        return self.order_item_repo.get_items_by_order(order_id)

    def update_order(
        self,
        order_id: int,
        items: List[OrderedItem_API],
        order_data: PlacedOrder_API,
    ) -> Dict:
        logger.info(f"Updating order {order_id}")
        existing_order = self.get_order_by_id(order_id, with_items=True)

        if order_data.placed_order_state:
            validated = self.validate_order_status(
                order_data.placed_order_state
            )
            self.validate_status_transition(
                existing_order.placed_order_state, validated
            )
            existing_order.placed_order_state = validated

        if order_data.order_discount is not None:
            existing_order.order_discount = order_data.order_discount

        existing_order.placed_order_last_mod = datetime.now()
        updated_order = self.order_repo.update_order(existing_order)

        if items:
            self.order_item_repo.bulk_delete_by_order(order_id)
            new_items = []
            for api_item in items:
                item = self.build_ordered_item_model(api_item)
                item.order_ref = order_id
                new_items.append(item)
            self.order_item_repo.bulk_create(new_items)

        return {
            'order': updated_order,
            'items_updated': len(items) if items else 0,
        }

    # ================================================================
    # LOCAL: INVOICE LOOKUP (used by workflow)
    # ================================================================

    def get_invoice_for_order(self, order: PlacedOrder) -> Invoice:
        if not order.placed_order_invoice:
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order,
                error="Order has no linked invoice",
                fields_attempted=["payment"],
            )
        invoice = self.invoice_repo.get_invoice_by_id(
            order.placed_order_invoice
        )
        if not invoice:
            raise OrderUpdateFailedException(
                order_id=order.id_placed_order,
                error=f"Invoice {order.placed_order_invoice} not found",
                fields_attempted=["payment"],
            )
        return invoice