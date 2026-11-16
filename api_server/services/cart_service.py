# services/cart_service.py
"""
Cart service — local operations only.

Responsibilities (strictly local):
  - validations (entity existence, catalog presence, cart contents)
  - model construction (Cart, OrderedItem, OrderedService, Payment,
    ProductConsumption, Invoice)
  - persistence via repositories
  - computing totals, invoice numbers, due dates
  - entity-level rollback (delete local rows)

Allowed collaborators:
  - repositories (CartRepository, OrderRepository, FinancialRepository, ...)
  - local helper services that have no I/O beyond repos
    (PersonService, PricingService)

Forbidden collaborators:
  - inventory_client, finance_client
  - any service that performs a remote call
  - state transitions on Cart / Invoice / Item / Service
    (those belong to CartWorkflow, gated by policies)

Every method that the workflow needs to reach is public (no leading
underscore). Anything that is only used internally stays private.
"""

import logging
import random
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from core.models.finance_models import PaymentCreate
from repositories.service_repository import ServiceRepository
from repositories.order_repository import OrderRepository
from repositories.financial_repository import FinancialRepository
from repositories.cart_repository import CartRepository
from repositories.product_repository import ProductRepository
from repositories.user_repository import UserRepository
from repositories.supplier_repository import SupplierRepository

from services.person_service import PersonService
from services.pricing_service import PricingService

from core.models.api_models import (
    Cart_API, OrderedItem_API, OrderedService_API, Delivery_API,
    Person_API, Payment_API,
)
from core.models.models import (
    Cart, OrderedItem, OrderedService, Product,
    Invoice, Payment, ProductConsumption, ProvidedService,
)

from core.exceptions.specific.cart_exceptions import (
    CartServiceException,
    CartNotFoundException,
    CartCreationFailedException,
    CartUpdateFailedException,
    CartDeleteFailedException,
    CartSupplierNotFoundException,
    CartSellerNotFoundException,
    CartBuyerNotFoundException,
    CartProductNotFoundException,
    CartStockRollbackException,
    CartInvoiceCreationException,
    CartPaymentCreationException,
    CartReceiptCreationException,
    CartDepositCreationException,
)
from core.exceptions.handler import (
    ProductNotFoundException,
    InsufficientStockException,
    ServiceNotFoundException,
)
from core.exceptions.specific.product_exceptions import (
    ProductQuantityNotEnoughException,
)

from core.logging_config import get_logger

logger = get_logger(__name__)


# ==================== Payment intent enum ====================

class PaymentIntent(str, Enum):
    """
    What kind of payment the client is expressing at cart creation time.

    NONE      → no payment field was sent; invoice stays unpaid
    FULL      → cart_payment == True; settle the whole total
    DEPOSIT   → cart_deposit == True; settle a partial amount
    DUE_DATE  → installment scheduled; invoice gets the due date, no payment yet
    """
    NONE = "none"
    FULL = "full"
    DEPOSIT = "deposit"
    DUE_DATE = "due_date"


# Payment statuses as stored in the DB (must match the backend enum)
_PAYMENT_STATUS_COMPLETED = "completed"
_PAYMENT_STATUS_PENDING = "pending"

# Payment methods that settle instantly
_INSTANT_METHODS = {"cash"}


class CartService:
    """
    Local-only cart operations.

    Every collaborator on this class is either a repository (local DB) or
    a pure-local helper service (PersonService, PricingService). No HTTP
    client is constructed here. Remote orchestration is CartWorkflow's job.
    """

    def __init__(self):
        # Repositories — local persistence only
        self.cart_repo = CartRepository()
        self.order_repo = OrderRepository()
        self.invoice_repo = FinancialRepository()
        self.product_repo = ProductRepository()
        self.user_repo = UserRepository()
        self.supplier_repo = SupplierRepository()
        self.service_repo = ServiceRepository()

        # Pure-local helper services (no I/O beyond repos)
        self.person_service = PersonService()
        self.pricing_service = PricingService()

    # ==================== Helpers ====================



    def parse_inventory_response(self, response: Dict) -> Dict:
        """Parse inventory response to extract stock status by product ID."""
        if not response:
            return {}

        result = {}

        if all(isinstance(v, dict) for v in response.values()):
            return response

        if "items" in response and isinstance(response["items"], list):
            for item in response["items"]:
                pid = item.get("product_id")
                if pid:
                    result[str(pid)] = item
            return result

        if "data" in response and isinstance(response["data"], list):
            for item in response["data"]:
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

    def detect_payment_intent(self, cart_data: Cart_API) -> PaymentIntent:
        """
        Classify what the client intended based on the fields they sent.

        Priority:
          1. deposit flag → DEPOSIT
          2. payment flag → FULL
          3. due date set without payment → DUE_DATE
          4. otherwise → NONE
        """
        if getattr(cart_data, "cart_deposit", False):
            return PaymentIntent.DEPOSIT
        if getattr(cart_data, "cart_payment", False):
            return PaymentIntent.FULL
        if getattr(cart_data, "cart_due_date", None):
            return PaymentIntent.DUE_DATE
        return PaymentIntent.NONE

    def resolve_initial_payment_status(self, method: str) -> str:
        """Cash settles instantly; everything else awaits gateway confirmation."""
        return (
            _PAYMENT_STATUS_COMPLETED
            if (method or "").lower() in _INSTANT_METHODS
            else _PAYMENT_STATUS_PENDING
        )

    def compute_new_invoice_status(
        self,
        invoice_total: float,
        current_completed_total: float,
        new_payment_amount: float,
        new_payment_status: str,
    ) -> str:
        """
        Derive the invoice status after a payment lands.
        Only `completed` payments contribute to the paid total.
        """
        if new_payment_status != _PAYMENT_STATUS_COMPLETED:
            return "unpaid"

        total_paid = current_completed_total + new_payment_amount
        if invoice_total <= 0:
            return "unpaid"
        if total_paid >= invoice_total:
            return "paid"
        if total_paid > 0:
            return "partially_paid"
        return "unpaid"

    # Backwards-compat aliases for callers using the old underscore names.
    _detect_payment_intent = detect_payment_intent
    _resolve_initial_payment_status = resolve_initial_payment_status
    _compute_new_invoice_status = compute_new_invoice_status

    # ==================== Payload builders (local, pure) ====================

    def build_payment_create_payload(
        self,
        cart: Cart,
        invoice: Invoice,
        payment_method: str,
        captured_amount: float,
    ) -> PaymentCreate:
        """
        Local: shape the payload the workflow hands to the finance client.

        `PaymentCreate` lives in `core.models.finance_models`. It expects
        `invoice_id`, `amount`, `payment_method`, `user_id`, optional
        `notes`, optional `payment_type`.
        """
        from core.models.finance_models import PaymentCreate

        return PaymentCreate(
            invoice_id=invoice.invoice_id,
            amount=captured_amount,
            payment_method=payment_method,
            user_id=cart.selling_user_id,
            notes=f"Cart #{cart.cart_id} payment",
            payment_type="payment",
        )

    def build_payment_transaction_details(
        self,
        cart: Cart,
        invoice: Invoice,
        payment_method: str,
    ) -> Dict[str, Any]:
        """Local: default transaction details for the finance confirm call."""
        return {
            "reference": (
                f"CART-{cart.cart_id}-"
                f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ),
            "cart_id": cart.cart_id,
            "invoice_id": invoice.invoice_id,
            "payment_method": payment_method,
            "notes": f"Payment for cart #{cart.cart_id}",
        }

    def build_ordered_reserve_payload(
        self, items: List[OrderedItem]
    ) -> List[Dict[str, Any]]:
        return [
            {
                "id": item.id_ordered_item,
                "quantity": Decimal(item.ordered_quantity),
                "product_id": item.product_id,
            }
            for item in items
        ]

    # ==================== Cart Retrieval ====================

    def get_cart_by_id(self, cart_id: int, eager_load: bool = True) -> Cart:
        cart = self.cart_repo.get_cart_by_id(cart_id, eager_load=eager_load)
        if not cart:
            logger.warning("Cart with ID %s not found", cart_id)
            raise CartNotFoundException(cart_id=cart_id)

        try:
            if hasattr(cart, "ordered_item") and cart.ordered_item:
                for item in cart.ordered_item:
                    _ = item.id_ordered_item
                    _ = item.product_id
            if hasattr(cart, "ordered_service") and cart.ordered_service:
                for service in cart.ordered_service:
                    _ = service.ordered_service_id
                    _ = service.service_id
        except Exception as e:
            logger.warning("Error loading cart relationships: %s", e)
            cart = self.cart_repo.get_cart_by_id(cart_id, eager_load=True)
            if not cart:
                raise CartNotFoundException(cart_id=cart_id)

        return cart

    def get_carts_by_provider(
        self, provider_id: int, offset: int = 0, limit: int = 100
    ) -> List[Cart]:
        return self.cart_repo.get_carts_by_provider(provider_id, offset, limit)

    def get_carts_by_seller(
        self, seller_id: int, offset: int = 0, limit: int = 100
    ) -> List[Cart]:
        return self.cart_repo.get_carts_by_seller(seller_id, offset, limit)

    def get_carts_by_buyer(
        self, buyer_id: int, offset: int = 0, limit: int = 100
    ) -> List[Cart]:
        return self.cart_repo.get_carts_by_buyer(buyer_id, offset, limit)

    def list_carts(
        self,
        provider_id: int = 0,
        seller_id: int = 0,
        buyer_id: int = 0,
        status: str = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Cart]:
        return self.cart_repo.list_carts(
            provider_id, seller_id, buyer_id, status, offset, limit
        )

    def get_cart_summary(self, cart_id: int) -> Dict[str, Any]:
        cart = self.get_cart_by_id(cart_id, eager_load=True)
        subtotal = 0.0
        item_count = 0
        service_count = 0

        if cart.ordered_item:
            for item in cart.ordered_item:
                subtotal += item.ordered_quantity * \
                    item.unit_price
                item_count += 1

        if cart.ordered_service:
            for service in cart.ordered_service:
                subtotal += service.subtotal
                service_count += 1

        return {
            "cart_id": cart_id,
            "subtotal": round(subtotal, 2),
            "total": round(cart.subtotal or subtotal, 2),
            "item_count": item_count,
            "service_count": service_count,
            "status": cart.cart_status,
            "updated_at": cart.updated_at,
        }

    def get_cart_items(self, cart_id: int) -> List[Dict[str, Any]]:
        cart = self.get_cart_by_id(cart_id, eager_load=True)
        items = []
        if cart.ordered_item:
            for item in cart.ordered_item:
                product = self.product_repo.get_product_by_id(item.product_id)
                items.append({
                    "id": item.id_ordered_item,
                    "product_id": item.product_id,
                    "product_name": (
                        product.generic_name if product else "Unknown"
                    ),
                    "quantity": item.ordered_quantity,
                    "unit_price": item.unit_price,
                    "total_price": (
                        item.ordered_quantity *
                        item.unit_price
                    ),
                    "vat_rate": item.vat_rate,
                    "discount_amount": item.discount_amount or 0,
                })
        return items

    def get_cart_services(self, cart_id: int) -> List[Dict[str, Any]]:
        cart = self.get_cart_by_id(cart_id, eager_load=True)
        services = []
        if cart.ordered_service:
            for service in cart.ordered_service:
                service_obj = self.service_repo.get_service_by_id(
                    service.service_id
                )
                services.append({
                    "id": service.ordered_service_id,
                    "service_id": service.service_id,
                    "service_name": (
                        service_obj.provided_service_name
                        if service_obj else "Unknown"
                    ),
                    "quantity": service.ordered_service_quantity,
                    "unit_price": service.unit_price,
                    "total_price": service.subtotal,
                    "scheduled_at": service.scheduled_at,
                })
        return services

    # ==================== Invoice lookup ====================

    def get_invoice_for_cart(self, cart: Cart) -> Invoice:
        """
        Local: fetch the Invoice attached to a Cart.

        `persist_cart` sets `cart.invoice_id = created_invoice.invoice_id`,
        so this reads that id back through the financial repository.
        """
        invoice_id = getattr(cart, "invoice_id", None)
        if not invoice_id:
            raise CartInvoiceCreationException(
                error=(
                    f"Cart {getattr(cart, 'cart_id', '?')} has no "
                    f"linked invoice"
                )
            )

        invoice = self.invoice_repo.get_invoice_by_id(invoice_id)
        if not invoice:
            raise CartInvoiceCreationException(
                error=(
                    f"Invoice {invoice_id} not found for cart "
                    f"{getattr(cart, 'cart_id', '?')}"
                )
            )
        return invoice

    # ==================== Entity / catalog validation (local) ====================

    async def validate_entities(
        self, provider_id: int, seller_user_id: int, buyer_user_id: int
    ) -> None:
        provider = self.supplier_repo.get_supplier_by_id(provider_id)
        if not provider:
            raise CartSupplierNotFoundException(provider_id=provider_id)

        selling_user = self.user_repo.get_by_id(seller_user_id)
        if not selling_user:
            raise CartSellerNotFoundException(seller_id=seller_user_id)

        if buyer_user_id > 0:
            buyer_user = self.user_repo.get_by_id(buyer_user_id)
            if not buyer_user:
                raise CartBuyerNotFoundException(buyer_id=buyer_user_id)

    async def load_products_and_services(
        self,
        ordered_items: List[OrderedItem_API],
        ordered_services: List[OrderedService_API],
    ) -> Tuple[Dict[int, Any], Dict[int, Any]]:
        product_ids = [item.product_id for item in ordered_items]
        service_ids = [
            service.ordered_service_service_id for service in ordered_services
        ]

        products: Dict[int, Any] = {}
        if product_ids:
            product_list = self.product_repo.get_products_by_ids(product_ids)
            products = {p.id_product: p for p in product_list}
            if len(products) != len(set(product_ids)):
                missing = set(product_ids) - set(products.keys())
                raise CartProductNotFoundException(
                    product_id=next(iter(missing))
                )

        services: Dict[int, Any] = {}
        if service_ids:
            service_list = self.service_repo.get_services_by_ids(service_ids)
            services = {s.idprovided_service: s for s in service_list}
            if len(services) != len(set(service_ids)):
                missing = set(service_ids) - set(services.keys())
                raise ServiceNotFoundException(service_id=next(iter(missing)))

        return products, services

    async def build_reservation_plan(
        self,
        ordered_items: List[OrderedItem_API],
        ordered_services: List[OrderedService_API],
        products: Dict[int, Any],
        services: Dict[int, Any],
    ) -> Tuple[Dict[int, Dict], Dict[int, Dict]]:
        reservation_plan: Dict[int, Dict] = {}
        item_details: Dict[int, Dict] = {}

        for item in ordered_items:
            product_id = item.product_id
            product = products.get(product_id)
            if not product:
                continue

            quantity = item.ordered_quantity
            reservation_plan.setdefault(
                product_id, {"quantity": 0, "sources": []}
            )
            reservation_plan[product_id]["quantity"] += quantity
            reservation_plan[product_id]["sources"].append({
                "type": "ordered_item",
                "id": getattr(item, "id_ordered_item", 0),
                "quantity": quantity,
            })

            item_details.setdefault(product_id, {
                "unit_price": product.unit_price,
                "product": product,
            })

        for service_api in ordered_services:
            service_id = service_api.ordered_service_service_id
            if service_id not in services:
                continue

            resource_requirements = (
                self.service_repo.get_service_resource_requirements(
                    service_id
                )
            )
            for requirement in resource_requirements or []:
                if not requirement.service_resource_requirement_is_consumable:
                    continue

                product_id = requirement.product_id
                if product_id is None:
                    continue

                quantity_needed = (
                    requirement.service_resource_requirement_quantity
                    * service_api.ordered_service_quantity
                )

                reservation_plan.setdefault(
                    product_id, {"quantity": 0, "sources": []}
                )
                reservation_plan[product_id]["quantity"] += quantity_needed
                reservation_plan[product_id]["sources"].append({
                    "type": "consumption",
                    "service_id": service_id,
                    "id": requirement.id_service_resource_requirement,
                    "quantity": quantity_needed,
                })

                if product_id not in item_details:
                    product = self.product_repo.get_product_by_id(product_id)
                    if product:
                        item_details[product_id] = {
                            "unit_price": product.unit_price,
                            "product": product,
                        }

        return reservation_plan, item_details

    # ==================== Cart building (local) ====================

    async def build_cart(
        self,
        ordered_items: List[OrderedItem_API],
        ordered_services: List[OrderedService_API],
        cart_data: Cart_API,
        products: Dict[int, Any],
        services: Dict[int, Any],
        item_details: Dict[int, Dict],
        provider_id: int,
        seller_user_id: int,
        buyer_user_id: int,
        client: Optional[Person_API],
    ) -> Tuple[Cart, float, Optional[Any]]:
        total_price = Decimal("0.0")
        ordered_item_models: List[OrderedItem] = []

        for item in ordered_items:
            product_id = item.product_id
            product = products.get(product_id)
            if not product:
                continue

            unit_price = product.unit_price
            item_total = item.ordered_quantity * unit_price
            if item.vat_rate:
                item_total *= 1 + item.vat_rate
            if getattr(item, "product_discount", None):
                item_total -= item.product_discount
            total_price += item_total

            ordered_item = OrderedItem(
                product_id=product_id,
                ordered_quantity=item.ordered_quantity,
                vat_rate=item.vat_rate,
                discount_amount=getattr(item, "product_discount", None),
                unit_price=unit_price,
                reserved_quantity=0,
            )
            order_id = getattr(item, "order_id", None)
            if order_id and order_id > 0:
                ordered_item.order_id = order_id
            ordered_item_models.append(ordered_item)

        ordered_service_models: List[OrderedService] = []
        for service_api in ordered_services:
            service_id = service_api.ordered_service_service_id
            service = services.get(service_id)
            if not service:
                continue

            unit_price = service.unit_price
            service_total = service_api.ordered_service_quantity * unit_price
            total_price += service_total

            ordered_service = OrderedService(
                service_id=service_id,
                ordered_service_quantity=service_api.ordered_service_quantity,
                unit_price=unit_price,
                subtotal=service_total,
                ordered_service_notes=service_api.ordered_service_notes,
                ordered_service_delivery_status="pending",
            )

            reqs = self.service_repo.get_service_resource_requirements(
                service_id
            )
            ordered_service.product_consumption = [
                ProductConsumption(
                    consumed_product_id=req.product_id,
                    requirement_id=req.id_service_resource_requirement,
                    product_reserved_quantity=0,
                )
                for req in reqs or []
                if req.service_resource_requirement_is_consumable
                and req.product_id is not None
            ]

            scheduled_at = getattr(
                service_api, "ordered_service_scheduled_at", None
            )
            if scheduled_at:
                ordered_service.scheduled_at = scheduled_at

            ordered_service_models.append(ordered_service)

        person_obj = None
        if client:
            if client.id_person == 0:
                person_obj = self.person_service.refresh_or_insert_person(client)
            else:
                person_obj = self.person_service.get_person_by_id(
                    client.id_person
                )

        final_total = round(
            cart_data.cart_total_amount or total_price, 2
        )

        cart = Cart(
            provider_id=provider_id,
            selling_user_id=seller_user_id,
            client_person_id=person_obj.id_person if person_obj else None,
            cart_status="open",
            subtotal=final_total,
            notes=cart_data.cart_notes or "",
        )

        if buyer_user_id:
            cart.client_user_id = buyer_user_id
        if cart_data.cart_due_date:
            cart.cart_due_date = cart_data.cart_due_date

        cart.ordered_item = ordered_item_models
        cart.ordered_service = ordered_service_models

        return cart, final_total, person_obj

    # ==================== Persist cart (local) ====================

    def get_consumption_snapshot_for_cart(
        self, cart_id: int
    ) -> List[Dict[str, Any]]:
        """Local: fetch product_consumption rows for a cart as dicts."""
        return self.cart_repo.get_consumption_snapshot_for_cart(cart_id)

    async def persist_cart(self, cart, total_price, person_obj):
        # 1. Snapshot the child data BEFORE persisting the cart, so we
        #    never need to read `cart.ordered_item` / `cart.ordered_service`
        #    after any commit.
        items_data = [
            {
                "product_id": i.product_id,
                "ordered_quantity": i.ordered_quantity,
                "vat_rate": i.vat_rate,
                "unit_price": i.unit_price,
                "discount_amount": i.discount_amount,
            }
            for i in cart.ordered_item or []
        ]
        services_data = [
            {
                "service_id": s.service_id,
                "ordered_service_quantity": s.ordered_service_quantity,
                "unit_price": s.unit_price,
                "subtotal": s.subtotal,
                "ordered_service_notes": s.ordered_service_notes,
                "ordered_service_delivery_status": s.ordered_service_delivery_status,
                "scheduled_at": s.scheduled_at,
                "consumptions": [
                    {
                        "consumed_product_id": c.consumed_product_id,
                        "requirement_id": c.requirement_id,
                    }
                    for c in (s.product_consumption or [])
                ],
            }
            for s in cart.ordered_service or []
        ]

        # 2. Detach the transients from the cart so `create_cart` doesn't
        #    cascade them and the request session doesn't hold them.
        cart.ordered_item = []
        cart.ordered_service = []

        # 3. Persist cart (only scalars now; cascade has nothing to flush).
        invoice = Invoice(
            grand_total=total_price,
            invoice_status="unpaid",
            invoice_issue_date=datetime.now().date(),
            invoice_due_date=datetime.now().date() + timedelta(days=30),
            invoice_type="invoice",
            tax_amount=0.0,
        )
        created_invoice = self.invoice_repo.create_invoice(invoice)
        cart.invoice_id = created_invoice.invoice_id
        cart = self.cart_repo.create_cart(cart)

        # 4. Create items from the snapshot, not from cart.ordered_item.
        created_items = []
        for data in items_data:
            item = OrderedItem(cart_id=cart.cart_id, reserved_quantity=0, **data)
            created = self.order_repo.create_order_item(item)
            created_items.append(created)

        # 5. Create services + consumptions from the snapshot.
        created_services = []
        consumption_snapshot = []
        for data in services_data:
            consumptions = data.pop("consumptions")
            service = OrderedService(cart_id=cart.cart_id, **data)
            service.product_consumption = [
                ProductConsumption(
                    consumed_product_id=c["consumed_product_id"],
                    requirement_id=c["requirement_id"],
                    product_reserved_quantity=0,
                )
                for c in consumptions
            ]
            created = self.cart_repo.create_ordered_service(service)
            created_services.append(created)
            for c in (created.product_consumption or []):
                consumption_snapshot.append({
                    "id": c.id_product_consumption,
                    "requirement_id": c.requirement_id,
                    "consumed_product_id": c.consumed_product_id,
                    "quantity": int(c.product_reserved_quantity or 0),
                    "ordered_service_id": created.ordered_service_id,
                })

        return (
            cart, created_items, created_services, created_invoice,
            consumption_snapshot,
        )



    # ==================== Payment & invoice persistence (local) ====================

    def create_payment_row(
        self,
        invoice_id: int,
        amount: float,
        method: str,
        status: str,
        notes: str = "",
    ) -> Payment:
        """
        Local: build and persist a Payment row directly via the repo.
        """
        payment = Payment(
            payment_invoice_id=invoice_id,
            payment_amount=amount,
            payment_method=method,
            payment_status=status,
            payment_reference=(
                f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-"
                f"{random.randint(100, 999)}"
            ),
            payment_notes=notes,
            payment_type="payment",
        )
        return self.invoice_repo.create_payment(payment)

    # Backwards-compat alias
    _create_payment = create_payment_row

    def apply_invoice_status(self, invoice: Invoice, new_status: str) -> None:
        """Local: write the invoice's new status via the repo."""
        invoice.invoice_status = new_status
        invoice.updated_at = datetime.now()
        try:
            self.invoice_repo.update_invoice(invoice)
        except Exception as e:
            logger.error(
                "Failed to update invoice %s status: %s",
                invoice.invoice_id, e,
            )
            raise CartInvoiceCreationException(
                error=f"Invoice status update failed: {e}"
            )

    # Backwards-compat alias
    _apply_invoice_status = apply_invoice_status

    # ==================== Cart status (local, policy-agnostic) ====================

    def update_cart_status(self, cart_id: int, new_status: str) -> Cart:
        """
        Local: set cart_status to `new_status` and persist.

        Does NOT validate the transition. Callers that need policy
        gating go through CartWorkflow.mark_cart_*.
        """
        logger.info("Updating cart %s status to %r", cart_id, new_status)
        cart = self.get_cart_by_id(cart_id)
        cart.cart_status = new_status
        cart.updated_at = datetime.now()

        try:
            result = self.cart_repo.update_cart(cart)
            logger.info("Cart %s status updated successfully", cart_id)
            return result
        except Exception as e:
            logger.error("Failed to update cart %s status: %s", cart_id, e)
            raise CartUpdateFailedException(
                cart_id=cart_id,
                error=str(e),
                fields_attempted=["cart_status"],
            )

    # ==================== Item / service lookup (repo passthrough) ====================

    def get_ordered_item(self, item_id: int) -> OrderedItem:
        """Local: fetch an OrderedItem or raise."""
        item = self.order_repo.get_ordered_item_by_id(item_id)
        if item is None:
            raise ValueError(f"OrderedItem {item_id} not found")
        return item

    def persist_ordered_item(self, item: OrderedItem) -> OrderedItem:
        """Local: persist an OrderedItem's changes."""
        item.updated_at = datetime.now()
        return self.order_repo.update_order_item(item)

    def get_ordered_service(self, service_id: int) -> OrderedService:
        """Local: fetch an OrderedService or raise."""
        svc = self.cart_repo.get_ordered_service_by_id(service_id)
        if svc is None:
            raise ValueError(f"OrderedService {service_id} not found")
        return svc

    def persist_ordered_service(self, svc: OrderedService) -> OrderedService:
        """Local: persist an OrderedService's changes."""
        svc.updated_at = datetime.now()
        return self.cart_repo.update_ordered_service(svc)

    # ==================== Rollback (local only) ====================

    async def rollback_cart_creation(
        self,
        cart: Optional[Cart],
        created_items: List[OrderedItem] = None,
    ) -> None:
        """
        Local: delete whatever was created.

        Remote release of inventory is the workflow's job — this method
        never calls the inventory client.
        """
        if not cart:
            return

        logger.info("Rolling back cart creation for cart %s", cart.cart_id)

        try:
            self.cart_repo.delete_cart_sync(cart)
            logger.info("Cart deleted during rollback")
        except Exception as e:
            logger.error("Rollback failed: %s", e)

    # Backwards-compat alias
    _rollback_cart_creation = rollback_cart_creation

    # ==================== Payment lookups (idempotency guards) ====================

    def get_completed_payment_for_invoice(
        self, invoice_id: int
    ) -> Optional[Payment]:
        """Local: find an existing completed payment for an invoice."""
        return self.invoice_repo.get_payment_by_invoice_and_status(
            invoice_id=invoice_id,
            status="completed",
        )

    def get_pending_payment_for_invoice(
        self, invoice_id: int
    ) -> Optional[Payment]:
        """Local: find an existing pending payment for an invoice."""
        return self.invoice_repo.get_payment_by_invoice_and_status(
            invoice_id=invoice_id,
            status="pending",
        )