"""
Cart router.

Routing rules:
  - Endpoints that cross a process boundary (inventory silo, finance
    service) depend on CartWorkflow.
  - Endpoints that only touch local entities depend on CartService.
  - Router never instantiates either directly — both come from dependency
    providers, so tests can override them.
"""

from fastapi import APIRouter, Depends, Query, status, Body, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
import logging

from services.helpers.auth.auth_dependencies import get_current_user_id
from core.exceptions.specific.cart_exceptions import (
    CartServiceException,
    CartNotFoundException,
    CartCreationFailedException,
    CartUpdateFailedException,
    CartDeleteFailedException,
    CartFilterRequiredException,
    CartInvalidStatusException,
    CartItemNotFoundException,
    CartServiceNotFoundException,
    CartPaymentRequiredException,
)
from core.models.api_models import (
    Cart_API, OrderedItem_API, OrderedService_API, Delivery_API, Person_API,
)
from core.response_models import (
    ErrorResponseModel,
    get_crud_error_responses,
)
from services.cart_service import CartService
from workflows.cart_workflow import CartWorkflow

from core.logging_config import get_logger

logger = get_logger(__name__)



# ==================== Router ====================

cart_router = APIRouter()


def get_cart_service() -> CartService:
    """Dependency: local reads/writes only."""
    return CartService()


def get_cart_workflow() -> CartWorkflow:
    """Dependency: orchestration (inventory + finance)."""
    return CartWorkflow()


# ==================== Request/Response Models ====================


class CartCreateRequest(BaseModel):
    """Request model for creating a cart."""

    provider_id: int = Field(..., gt=0, description="Provider ID")
    seller_user_id: int = Field(..., gt=0, description="Seller user ID")
    buyer_user_id: Optional[int] = Field(None, description="Buyer user ID")
    cart: Cart_API = Field(..., description="Cart data (includes optional payment fields)")
    ordered_items: Optional[List[OrderedItem_API]] = Field(
        default_factory=list, description="Ordered items"
    )
    ordered_services: Optional[List[OrderedService_API]] = Field(
        default_factory=list, description="Ordered services"
    )
    client: Optional[Person_API] = Field(None, description="Client information")
    delivery: Optional[Delivery_API] = Field(None, description="Delivery information")

    @model_validator(mode="after")
    def validate_cart_content(self):
        """Ensure cart has at least one item or service."""
        if not self.ordered_items and not self.ordered_services:
            raise ValueError("Cart must have at least one ordered item or service")
        return self


class CartListResponse(BaseModel):
    """Response model for cart list."""

    data: List[Dict[str, Any]]
    filter: Dict[str, Any]
    pagination: Dict[str, Any]


class CreateCartResponse(BaseModel):
    """Response model for cart creation."""

    success: bool
    message: str
    data: Dict[str, Any]


class UpdateCartStatusResponse(BaseModel):
    """Response model for cart status update."""

    success: bool
    message: str
    data: Dict[str, Any]


class DeleteCartResponse(BaseModel):
    """Response model for cart deletion."""

    success: bool
    message: str
    data: Dict[str, Any]


class CartSummaryResponse(BaseModel):
    """Response model for cart summary."""

    cart_id: int
    cart_status: str
    items: Dict[str, Any]
    services: Dict[str, Any]
    total_amount: float
    currency: str
    delivery: Optional[Dict[str, Any]] = None


# ==================== Response helpers ====================


def _build_financial_documents_payload(
    financial_docs: Optional[Dict[str, Any]],
) -> Dict[str, bool]:
    """Boolean map the client can rely on regardless of what was created."""
    if not financial_docs:
        return {
            "has_invoice": False,
            "has_payment": False,
            "has_receipt": False,
            "has_deposit": False,
        }

    return {
        "has_invoice": "invoice" in financial_docs,
        "has_payment": "payment" in financial_docs,
        "has_receipt": "receipt" in financial_docs,
        "has_deposit": "deposit" in financial_docs,
    }


def _serialize_cart_short(cart) -> Dict[str, Any]:
    """Compact cart representation used by list endpoints."""
    return {
        "cart_id": cart.cart_id,
        "provider_id": cart.cart_product_provider_id,
        "selling_user": cart.cart_selling_user,
        "client_user": cart.cart_client_user,
        "status": cart.cart_status,
        "total_amount": float(cart.cart_total_amount or 0),
        "notes": cart.cart_notes,
        "created_at": cart.cart_created_at.isoformat() if cart.cart_created_at else None,
        "updated_at": cart.cart_updated_at.isoformat() if cart.cart_updated_at else None,
        "due_date": cart.cart_due_date.isoformat() if cart.cart_due_date else None,
        "invoice_id": cart.cart_invoice,
        "person_ref": cart.cart_person_ref,
    }


def _serialize_ordered_item(item) -> Dict[str, Any]:
    return {
        "id": item.id_ordered_item,
        "product_id": item.ordered_product_id,
        "quantity": item.ordered_quantity,
        "unit_price": float(item.unit_price) if item.unit_price else 0,
        "total_price": float(item.unit_price * item.ordered_quantity) if item.unit_price else 0,
        "vat": float(item.applied_vat) if item.applied_vat else 0,
        "discount": float(item.product_discount) if item.product_discount else 0,
        "delivery_status": item.ordered_item_delivery_status,
        "delivery_fee": float(item.ordered_item_delivery_fee) if item.ordered_item_delivery_fee else 0,
    }


def _serialize_ordered_service(service) -> Dict[str, Any]:
    return {
        "id": service.ordered_service_id,
        "service_id": service.ordered_service_service_id,
        "quantity": service.ordered_service_quantity,
        "unit_price": float(service.ordered_service_unit_price) if service.ordered_service_unit_price else 0,
        "total_price": float(service.ordered_service_total_price) if service.ordered_service_total_price else 0,
        "notes": service.ordered_service_notes,
        "scheduled_at": service.ordered_service_scheduled_at.isoformat() if service.ordered_service_scheduled_at else None,
        "delivery_status": service.ordered_service_delivery_status,
        "delivery_fee": float(service.ordered_service_delivery_fee) if service.ordered_service_delivery_fee else 0,
    }


# ==================== Cart Listing (service only) ====================


@cart_router.get(
    "/carts",
    summary="List carts",
    description="Get carts with filters. At least one filter is required.",
)
def get_carts(
    provider_id: Optional[int] = Query(0, description="Filter by provider ID"),
    seller_id: Optional[int] = Query(0, description="Filter by seller ID"),
    buyer_id: Optional[int] = Query(0, description="Filter by buyer ID"),
    status: Optional[str] = Query(None, description="Filter by cart status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    cart_service: CartService = Depends(get_cart_service),
):
    """Get carts with filters. At least one filter is required."""
    if not any([provider_id, seller_id, buyer_id, status]):
        raise CartFilterRequiredException(
            details={
                "required_filters": [
                    "provider_id",
                    "seller_id",
                    "buyer_id",
                    "status",
                ]
            }
        )

    carts, total = cart_service.list_carts(
        provider_id=provider_id or 0,
        seller_id=seller_id or 0,
        buyer_id=buyer_id or 0,
        status=status,
        offset=offset,
        limit=limit,
    )

    return {
        "data": [_serialize_cart_short(c) for c in carts],
        "filter": {
            "provider_id": provider_id,
            "seller_id": seller_id,
            "buyer_id": buyer_id,
            "status": status,
        },
        "pagination": {"offset": offset, "limit": limit, "total": total},
    }


# ==================== Single Cart Reads (service only) ====================


@cart_router.get(
    "/carts/{cart_id}",
    summary="Get cart by ID",
    description="Retrieve a specific cart by its ID.",
    responses={
        200: {"description": "Cart retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
def get_cart(
    cart_id: int,
    cart_service: CartService = Depends(get_cart_service),
):
    """Get cart by ID with related items, services, and invoice."""
    logger.info(f"Fetching cart with ID: {cart_id}")

    try:
        cart = cart_service.get_cart_by_id(cart_id, eager_load=True)
        if not cart:
            raise CartNotFoundException(cart_id=cart_id)

        ordered_items = []
        if hasattr(cart, "ordered_item") and cart.ordered_item:
            ordered_items = [_serialize_ordered_item(i) for i in cart.ordered_item]

        ordered_services = []
        if hasattr(cart, "ordered_service") and cart.ordered_service:
            ordered_services = [_serialize_ordered_service(s) for s in cart.ordered_service]

        return {
            **_serialize_cart_short(cart),
            "ordered_items": ordered_items,
            "ordered_services": ordered_services,
        }

    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch cart {cart_id}: {e}")
        raise CartNotFoundException(cart_id=cart_id, details={"error": str(e)})


# ==================== Cart Creation (workflow) ====================


@cart_router.post(
    "/carts",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new cart",
    description=(
        "Creates a new cart with items, services, delivery, and optional payment "
        "capture driven by the `cart` payload fields:\n"
        "- `cart_payment` / `cart_deposit` → intent\n"
        "- `cart_paid_money` → amount charged now\n"
        "- `cart_payment_method` → 'cash' auto-completes; others stay pending\n\n"
        "Orchestrates inventory availability check, local persistence, "
        "inventory reservation, and inventory confirmation."
    ),
    responses={
        201: {"description": "Cart created successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
        417: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
async def create_cart(
    request: CartCreateRequest = Body(...),
    user_id: int = Depends(get_current_user_id),
    workflow: CartWorkflow = Depends(get_cart_workflow),
):
    """
    Create a new cart.

    If the client declares a payment intent in the `cart` payload and
    provides a non-zero `cart_paid_money`, a corresponding payment record
    is created as part of the same request and the invoice status is
    updated accordingly.
    """
    logger.info(
        f"Creating cart - provider:{request.provider_id}, "
        f"seller:{request.seller_user_id}, "
        f"payment_intent=("
        f"payment={getattr(request.cart, 'cart_payment', False)}, "
        f"deposit={getattr(request.cart, 'cart_deposit', False)}, "
        f"amount={getattr(request.cart, 'cart_paid_money', 0)}, "
        f"method={getattr(request.cart, 'cart_payment_method', None)}"
        f")"
    )

    try:
        financial_docs, created_cart = await workflow.create_cart(
            ordered_items=request.ordered_items,
            ordered_services=request.ordered_services,
            cart_data=request.cart,
            delivery=request.delivery,
            client=request.client,
            provider_id=request.provider_id,
            seller_user_id=request.seller_user_id,
            buyer_user_id=request.buyer_user_id or 0,
        )

        logger.info(
            f"✅ Cart {created_cart.cart_id} created "
            f"(total={created_cart.cart_total_amount}, "
            f"invoice={created_cart.cart_invoice})"
        )

        financial_payload = _build_financial_documents_payload(financial_docs)
        logger.info(f"Financial documents: {financial_payload}")

        return {
            "success": True,
            "message": "Cart created successfully",
            "data": {
                "cart_id": created_cart.cart_id,
                "cart_invoice": created_cart.cart_invoice,
                "status": created_cart.cart_status,
                "total_amount": (
                    float(created_cart.cart_total_amount)
                    if created_cart.cart_total_amount is not None
                    else 0
                ),
                "created_at": (
                    created_cart.cart_created_at.isoformat()
                    if created_cart.cart_created_at
                    else None
                ),
                "financial_documents": financial_payload,
            },
        }

    except (CartCreationFailedException, CartPaymentRequiredException):
        raise
    except Exception as e:
        logger.error(f"Failed to create cart: {e}")
        raise CartCreationFailedException(
            error=str(e),
            provider_id=request.provider_id,
            seller_id=request.seller_user_id,
            buyer_id=request.buyer_user_id or 0,
        )


# ==================== Payment / Inventory (workflow) ====================


@cart_router.post(
    "/carts/{cart_id}/pay",
    summary="Process payment for a cart",
    description=(
        "Creates and confirms a payment for the cart's invoice, marks the "
        "invoice paid (or partially paid), and advances the local state "
        "via InvoicePolicy. Idempotent on already-paid invoices."
    ),
    responses={
        200: {"description": "Payment processed"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
async def process_cart_payment(
    cart_id: int,
    payment_method: str = Query("card", description="Payment method"),
    captured_amount: Optional[float] = Query(
        None, description="Amount captured (omit to assert full payment)"
    ),
    user_id: int = Depends(get_current_user_id),
    workflow: CartWorkflow = Depends(get_cart_workflow),
):
    """Phase 2 of the cart workflow."""
    logger.info(f"Processing payment for cart {cart_id}")

    try:
        return await workflow.process_payment(
            cart_id=cart_id,
            payment_method=payment_method,
            captured_amount=captured_amount,
        )
    except CartNotFoundException:
        raise
    except ValueError as e:
        # Policy denial surfaces here
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to process payment for cart {cart_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {e}",
        )


@cart_router.post(
    "/carts/{cart_id}/confirm-inventory",
    summary="Confirm inventory for a cart",
    description=(
        "Converts reserved inventory into a real deduction. Call after "
        "payment succeeds. Idempotent."
    ),
    responses={
        200: {"description": "Inventory confirmed"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
async def confirm_cart_inventory(
    cart_id: int,
    user_id: int = Depends(get_current_user_id),
    workflow: CartWorkflow = Depends(get_cart_workflow),
):
    """Phase 3 of the cart workflow."""
    logger.info(f"Confirming inventory for cart {cart_id}")

    try:
        return await workflow.confirm_inventory_for_cart(cart_id)
    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm inventory for cart {cart_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inventory confirmation failed: {e}",
        )


@cart_router.post(
    "/carts/{cart_id}/finalize",
    summary="Finalize a cart (payment + inventory)",
    description=(
        "Convenience endpoint that runs payment and inventory confirmation "
        "back-to-back. Use when the caller wants the synchronous behavior."
    ),
    responses={
        200: {"description": "Cart finalized"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
async def finalize_cart(
    cart_id: int,
    payment_method: str = Query("card", description="Payment method"),
    captured_amount: Optional[float] = Query(
        None, description="Amount captured (omit to assert full payment)"
    ),
    user_id: int = Depends(get_current_user_id),
    workflow: CartWorkflow = Depends(get_cart_workflow),
):
    logger.info(f"Finalizing cart {cart_id}")

    try:
        return await workflow.finalize_cart(
            cart_id=cart_id,
            payment_method=payment_method,
            captured_amount=captured_amount,
        )
    except CartNotFoundException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to finalize cart {cart_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finalization failed: {e}",
        )


# ==================== Cart Status (workflow, policy-gated) ====================


@cart_router.patch(
    "/carts/{cart_id}/status",
    summary="Update cart status",
    description=(
        "Update the status of a cart. The transition is validated by "
        "CartPolicy — illegal transitions return 400."
    ),
    responses={
        200: {"description": "Cart status updated successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
async def update_cart_status(
    cart_id: int,
    status: str = Query(
        ...,
        description=(
            "New cart status "
            "(open, pending, completed, canceled, partial, checkout, abandoned)"
        ),
    ),
    user_id: int = Depends(get_current_user_id),
    workflow: CartWorkflow = Depends(get_cart_workflow),
    cart_service: CartService = Depends(get_cart_service),
):
    """
    Update cart status via the policy-gated transitions exposed by the
    workflow. Only the transitions the policy allows are accepted.
    """
    logger.info(f"Updating status for cart {cart_id} to '{status}'")

    valid_statuses = [
        "open",
        "pending",
        "completed",
        "canceled",
        "partial",
        "checkout",
        "abandoned",
    ]

    normalized = status.lower()
    if normalized not in valid_statuses:
        raise CartInvalidStatusException(
            cart_id=cart_id,
            requested_status=status,
            allowed_statuses=valid_statuses,
        )

    try:
        existing_cart = cart_service.get_cart_by_id(cart_id)
        previous_status = existing_cart.cart_status

        # Dispatch to the correct workflow transition method. Each one
        # applies the policy gate and persists the new status.
        dispatch = {
            "pending":    lambda: workflow.mark_cart_pending(cart_id),
            "checkout":   lambda: workflow.mark_cart_checkout(cart_id),
            "completed":  lambda: workflow.mark_cart_completed(cart_id),
            "partial":    lambda: workflow.mark_cart_partial(cart_id),
            "abandoned":  lambda: workflow.mark_cart_abandoned(cart_id),
            "open":       lambda: workflow.reopen_cart(cart_id),
            "canceled":   lambda: workflow.cancel_cart(cart_id),
        }

        result = await dispatch[normalized]()

        logger.info(f"Cart {cart_id} status updated to '{normalized}'")
        return {
            "success": True,
            "message": f"Cart status updated to '{normalized}'",
            "data": {
                "cart_id": cart_id,
                "new_status": result.get("new_status", normalized),
                "previous_status": result.get("previous_status", previous_status),
                "side_effects": result.get("side_effects", []),
                "updated_at": datetime.now().isoformat(),
            },
        }

    except CartNotFoundException:
        raise
    except CartInvalidStatusException:
        raise
    except ValueError as e:
        # Policy denial
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update status for cart {cart_id}: {e}")
        raise CartUpdateFailedException(
            cart_id=cart_id,
            error=str(e),
            fields_attempted=["status"],
        )


# ==================== Cart Delete (workflow) ====================


@cart_router.delete(
    "/carts/{cart_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a cart",
    description=(
        "Deletes a cart, releasing reserved inventory remotely first, "
        "then removing local rows."
    ),
    responses={
        200: {"description": "Cart deleted successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
async def delete_cart(
    cart_id: int,
    force_delete: bool = Query(
        False, description="Force delete even if cart has items or services"
    ),
    user_id: int = Depends(get_current_user_id),
    workflow: CartWorkflow = Depends(get_cart_workflow),
    cart_service: CartService = Depends(get_cart_service),
):
    """Delete a cart."""
    logger.info(f"Deleting cart with ID: {cart_id} (force={force_delete})")

    try:
        existing_cart = cart_service.get_cart_by_id(cart_id)
        if not existing_cart:
            raise CartNotFoundException(cart_id=cart_id)

        has_items = (
            hasattr(existing_cart, "ordered_item")
            and len(existing_cart.ordered_item) > 0
        )
        has_services = (
            hasattr(existing_cart, "ordered_service")
            and len(existing_cart.ordered_service) > 0
        )

        if (has_items or has_services) and not force_delete:
            raise CartDeleteFailedException(
                cart_id=cart_id,
                error=(
                    "Cart has items and/or services. "
                    "Use force_delete=true to delete."
                ),
            )

        success = await workflow.delete_cart(cart_id)
        if not success:
            raise CartDeleteFailedException(
                cart_id=cart_id, error="Service returned False"
            )

        logger.info(f"Cart {cart_id} deleted successfully")
        return {
            "success": True,
            "message": f"Cart {cart_id} deleted successfully",
            "data": {"cart_id": cart_id, "force_deleted": force_delete},
        }

    except (CartNotFoundException, CartDeleteFailedException):
        raise
    except Exception as e:
        logger.error(f"Failed to delete cart {cart_id}: {e}")
        raise CartDeleteFailedException(cart_id=cart_id, error=str(e))


# ==================== Cart Item / Service Reads (service only) ====================


@cart_router.get(
    "/carts/{cart_id}/items",
    summary="Get cart items",
    description="Retrieve all items in a specific cart.",
    responses={
        200: {"description": "Items retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
def get_cart_items(
    cart_id: int,
    cart_service: CartService = Depends(get_cart_service),
):
    """Get items in a cart."""
    logger.info(f"Fetching items for cart ID: {cart_id}")

    try:
        cart = cart_service.get_cart_by_id(cart_id, eager_load=True)
        if not cart:
            raise CartNotFoundException(cart_id=cart_id)

        items = []
        if hasattr(cart, "ordered_item") and cart.ordered_item:
            items = [_serialize_ordered_item(i) for i in cart.ordered_item]

        return items

    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch items for cart {cart_id}: {e}")
        raise CartItemNotFoundException(cart_id=cart_id, details={"error": str(e)})


@cart_router.get(
    "/carts/{cart_id}/services",
    summary="Get cart services",
    description="Retrieve all services in a specific cart.",
    responses={
        200: {"description": "Services retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
def get_cart_services(
    cart_id: int,
    cart_service: CartService = Depends(get_cart_service),
):
    """Get services in a cart."""
    logger.info(f"Fetching services for cart ID: {cart_id}")

    try:
        cart = cart_service.get_cart_by_id(cart_id, eager_load=True)
        if not cart:
            raise CartNotFoundException(cart_id=cart_id)

        services = []
        if hasattr(cart, "ordered_service") and cart.ordered_service:
            services = [_serialize_ordered_service(s) for s in cart.ordered_service]

        return services

    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch services for cart {cart_id}: {e}")
        raise CartServiceNotFoundException(
            cart_id=cart_id, details={"error": str(e)}
        )


# ==================== Cart Summary (service only) ====================


@cart_router.get(
    "/carts/{cart_id}/summary",
    summary="Get cart summary",
    description="Get a summary of the cart including totals and counts.",
    responses={
        200: {"description": "Cart summary retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False),
    },
)
def get_cart_summary(
    cart_id: int,
    cart_service: CartService = Depends(get_cart_service),
):
    """Get cart summary with totals and counts."""
    logger.info(f"Fetching summary for cart ID: {cart_id}")

    try:
        cart = cart_service.get_cart_by_id(cart_id, eager_load=True)
        if not cart:
            raise CartNotFoundException(cart_id=cart_id)

        items = []
        total_items_amount = 0.0
        if hasattr(cart, "ordered_item") and cart.ordered_item:
            for item in cart.ordered_item:
                item_total = (
                    float(item.unit_price * item.ordered_quantity)
                    if item.unit_price
                    else 0
                )
                items.append(
                    {
                        "id": item.id_ordered_item,
                        "product_id": item.ordered_product_id,
                        "quantity": item.ordered_quantity,
                        "unit_price": float(item.unit_price) if item.unit_price else 0,
                        "total": item_total,
                    }
                )
                total_items_amount += item_total

        services = []
        total_services_amount = 0.0
        if hasattr(cart, "ordered_service") and cart.ordered_service:
            for service in cart.ordered_service:
                service_total = (
                    float(service.ordered_service_total_price)
                    if service.ordered_service_total_price
                    else 0
                )
                services.append(
                    {
                        "id": service.ordered_service_id,
                        "service_id": service.ordered_service_service_id,
                        "quantity": service.ordered_service_quantity,
                        "unit_price": (
                            float(service.ordered_service_unit_price)
                            if service.ordered_service_unit_price
                            else 0
                        ),
                        "total": service_total,
                    }
                )
                total_services_amount += service_total

        total_amount = total_items_amount + total_services_amount

        return {
            "cart_id": cart_id,
            "cart_status": cart.cart_status,
            "items": {
                "count": len(items),
                "total_amount": total_items_amount,
                "items": items,
            },
            "services": {
                "count": len(services),
                "total_amount": total_services_amount,
                "services": services,
            },
            "total_amount": total_amount,
            "currency": "DZD",
            "created_at": (
                cart.cart_created_at.isoformat() if cart.cart_created_at else None
            ),
            "updated_at": (
                cart.cart_updated_at.isoformat() if cart.cart_updated_at else None
            ),
        }

    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch summary for cart {cart_id}: {e}")
        raise CartServiceException(
            message="Failed to retrieve cart summary",
            details={"cart_id": cart_id, "error": str(e)},
        )