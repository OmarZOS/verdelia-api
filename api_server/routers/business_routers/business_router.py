# routers/business_router.py
"""
Main business router for legacy/compatibility endpoints and payment operations.

Real payment endpoints (matching OpenAPI spec):
    POST   /business/payments                → create payment
    GET    /business/payments                → list payments (filter by invoice_id)
    GET    /business/payments/{payment_id}   → fetch one payment

Legacy compatibility endpoints (kept for older clients):
    POST   /business/payment                 → wrapper for the three financial item types
    GET    /business/doc/...                 → paginated financial document fetch
"""

from fastapi import APIRouter, Depends, Query, status, Path, Body
from typing import List, Optional, Dict, Any
import logging

from core.exceptions.specific.finance_exceptions import (
    FinancialItemNotFoundException,
    PaymentCreationFailedException,
    PaymentNotFoundException,
)
from core.models.api_models import (
    Cart_API, Delivery_API, Payment_API, Deposit_API, AdditionalFee_API,
    OrderedItem_API, OrderedService_API, Person_API, PlacedOrder_API,
    ProvidedService_API, ServiceResourceRequirement_API, ServiceStaffRequirement_API,
)
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.cart_exceptions import (
    CartCreationFailedException,
    CartNotFoundException,
)
from services.cart_service import CartService
from services.financial_service import FinancialService

from core.logging_config import get_logger

logger = get_logger(__name__)


business_router = APIRouter()


# ==================== Dependencies ====================


def get_cart_service() -> CartService:
    return CartService()


def get_financial_service() -> FinancialService:
    return FinancialService()


# ==================== Payment Endpoints (real, spec-compliant) ====================


@business_router.post(
    "/business/payments",
    status_code=status.HTTP_201_CREATED,
    summary="Create payment",
    description=(
        "Create a payment against an invoice.\n\n"
        "- `payment_status` is set at creation and immutable afterward.\n"
        "- Valid statuses (uppercase): `PENDING`, `PAID`, `FAILED`, `REFUNDED`.\n"
        "- If `payment_status` is omitted, the server defaults to `PENDING`."
    ),
    responses={
        201: {"description": "Payment created successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True, include_409=True),
    },
)
def create_payment(
    payment: Payment_API = Body(...),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """
    Create a payment.

    Note: The service creates a local Payment row. Whether it also forwards
    to the external Finance microservice depends on
    `FinancialService.create_payment`.
    """
    logger.info(
        f"Creating payment - invoice:{payment.payment_invoice_id}, "
        f"amount:{payment.payment_amount}, "
        f"method:{payment.payment_method}, "
        f"status:{payment.payment_status}"
    )

    try:
        created = financial_service.create_payment(payment)

        return {
            "success": True,
            "message": "Payment created successfully",
            "data": {
                "payment_id": getattr(created, "payment_id", None),
                "payment_invoice_id": getattr(created, "payment_invoice_id", None),
                "payment_amount": float(getattr(created, "payment_amount", 0) or 0),
                "payment_method": getattr(created, "payment_method", None),
                "payment_status": getattr(created, "payment_status", None),
                "payment_reference": getattr(created, "payment_reference", None),
                "payment_created_at": (
                    created.payment_created_at.isoformat()
                    if getattr(created, "payment_created_at", None)
                    else None
                ),
            },
        }

    except PaymentCreationFailedException:
        raise
    except Exception as e:
        logger.error(f"Failed to create payment: {e}")
        raise PaymentCreationFailedException(
            error=str(e),
            details={
                "invoice_id": payment.payment_invoice_id,
                "amount": payment.payment_amount,
            },
        )

# ==================== Payment Lifecycle Actions ====================


@business_router.patch(
    "/business/payments/{payment_id}/status",
    summary="Update payment status",
    description=(
        "Transition a payment to a new status.\n\n"
        "Valid statuses (uppercase): `PENDING`, `PAID`, `FAILED`, `REFUNDED`.\n\n"
        "Allowed transitions:\n"
        "- `PENDING`  → `PAID`, `FAILED`\n"
        "- `PAID`     → `REFUNDED`\n"
        "- `FAILED`   → `PENDING` (retry)\n"
        "- `REFUNDED` → terminal\n\n"
        "Use this to simulate a gateway callback or a manual admin override."
    ),
    responses={
        200: {"description": "Payment status updated successfully"},
        400: {"model": ErrorResponseModel, "description": "Invalid transition"},
        404: {"model": ErrorResponseModel, "description": "Payment not found"},
        **get_crud_error_responses(include_404=False),
    },
)
def update_payment_status(
    payment_id: int = Path(..., gt=0, description="Payment ID"),
    new_status: str = Query(
        ...,
        description="New payment status: PENDING | PAID | FAILED | REFUNDED",
    ),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Update a payment's status with transition validation."""
    logger.info(f"Updating payment {payment_id} status to '{new_status}'")

    try:
        updated = financial_service.update_payment_status(
            payment_id=payment_id,
            new_status=new_status.upper(),
        )

        return {
            "success": True,
            "message": f"Payment {payment_id} status updated to '{updated.payment_status}'",
            "data": {
                "payment_id": updated.payment_id,
                "payment_status": updated.payment_status,
                "payment_invoice_id": updated.payment_invoice_id,
                "payment_amount": float(updated.payment_amount or 0),
                "payment_updated_at": (
                    updated.payment_updated_at.isoformat()
                    if getattr(updated, "payment_updated_at", None)
                    else None
                ),
            },
        }

    except PaymentNotFoundException:
        raise
    except PaymentCreationFailedException:
        raise
    except Exception as e:
        logger.error(f"Failed to update payment {payment_id} status: {e}")
        raise PaymentCreationFailedException(
            error=str(e),
            details={"payment_id": payment_id, "requested_status": new_status},
        )


@business_router.post(
    "/business/payments/{payment_id}/confirm",
    summary="Confirm a pending payment",
    description=(
        "Convenience wrapper that transitions a `PENDING` payment to `PAID`.\n"
        "Rejects if the payment is not currently `PENDING`."
    ),
    responses={
        200: {"description": "Payment confirmed"},
        400: {"model": ErrorResponseModel, "description": "Payment is not pending"},
        404: {"model": ErrorResponseModel, "description": "Payment not found"},
    },
)
def confirm_payment(
    payment_id: int = Path(..., gt=0),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Confirm a pending payment (PENDING → PAID)."""
    logger.info(f"Confirming payment {payment_id}")

    try:
        updated = financial_service.update_payment_status(
            payment_id=payment_id,
            new_status="PAID",
        )
        return {
            "success": True,
            "message": f"Payment {payment_id} confirmed",
            "data": {
                "payment_id": updated.payment_id,
                "payment_status": updated.payment_status,
            },
        }
    except PaymentNotFoundException:
        raise
    except PaymentCreationFailedException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm payment {payment_id}: {e}")
        raise PaymentCreationFailedException(error=str(e))


@business_router.post(
    "/business/payments/{payment_id}/reject",
    summary="Reject a pending payment",
    description=(
        "Convenience wrapper that transitions a `PENDING` payment to `FAILED`.\n"
        "Optionally records a reason in the payment notes."
    ),
    responses={
        200: {"description": "Payment rejected"},
        400: {"model": ErrorResponseModel, "description": "Payment is not pending"},
        404: {"model": ErrorResponseModel, "description": "Payment not found"},
    },
)
def reject_payment(
    payment_id: int = Path(..., gt=0),
    reason: Optional[str] = Body(None, embed=True),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Reject a pending payment (PENDING → FAILED)."""
    logger.info(f"Rejecting payment {payment_id} (reason={reason!r})")

    try:
        updated = financial_service.update_payment_status(
            payment_id=payment_id,
            new_status="FAILED",
            note=reason,
        )
        return {
            "success": True,
            "message": f"Payment {payment_id} rejected",
            "data": {
                "payment_id": updated.payment_id,
                "payment_status": updated.payment_status,
            },
        }
    except PaymentNotFoundException:
        raise
    except PaymentCreationFailedException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject payment {payment_id}: {e}")
        raise PaymentCreationFailedException(error=str(e))


@business_router.post(
    "/business/payments/{payment_id}/refund",
    summary="Refund a completed payment",
    description=(
        "Convenience wrapper that transitions a `PAID` payment to `REFUNDED`.\n"
        "For partial refunds, create a new payment row instead — this endpoint "
        "marks the entire payment as refunded."
    ),
    responses={
        200: {"description": "Payment refunded"},
        400: {"model": ErrorResponseModel, "description": "Payment is not paid"},
        404: {"model": ErrorResponseModel, "description": "Payment not found"},
    },
)
def refund_payment(
    payment_id: int = Path(..., gt=0),
    reason: Optional[str] = Body(None, embed=True),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Refund a paid payment (PAID → REFUNDED)."""
    logger.info(f"Refunding payment {payment_id} (reason={reason!r})")

    try:
        updated = financial_service.update_payment_status(
            payment_id=payment_id,
            new_status="REFUNDED",
            note=reason,
        )
        return {
            "success": True,
            "message": f"Payment {payment_id} refunded",
            "data": {
                "payment_id": updated.payment_id,
                "payment_status": updated.payment_status,
            },
        }
    except PaymentNotFoundException:
        raise
    except PaymentCreationFailedException:
        raise
    except Exception as e:
        logger.error(f"Failed to refund payment {payment_id}: {e}")
        raise PaymentCreationFailedException(error=str(e))

@business_router.get(
    "/business/payments",
    summary="List payments",
    description="List payments, optionally filtered by invoice ID.",
    responses={
        200: {"description": "Payments retrieved successfully"},
        500: {"model": ErrorResponseModel},
    },
)
def list_payments(
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """
    List payments with pagination.
    """
    logger.info(f"Listing payments - invoice_id:{invoice_id}, offset:{offset}, limit:{limit}")

    try:
        payments = financial_service.get_payments(invoice_id, offset, limit) or []

        return {
            "success": True,
            "message": f"Retrieved {len(payments)} payments",
            "data": [
                {
                    "payment_id": getattr(p, "payment_id", None),
                    "payment_invoice_id": getattr(p, "payment_invoice_id", None),
                    "payment_amount": float(getattr(p, "payment_amount", 0) or 0),
                    "payment_method": getattr(p, "payment_method", None),
                    "payment_status": getattr(p, "payment_status", None),
                    "payment_reference": getattr(p, "payment_reference", None),
                    "payment_notes": getattr(p, "payment_notes", None),
                    "payment_created_at": (
                        p.payment_created_at.isoformat()
                        if getattr(p, "payment_created_at", None)
                        else None
                    ),
                }
                for p in payments
            ],
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": len(payments),
            },
        }

    except Exception as e:
        logger.error(f"Failed to list payments: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})


@business_router.get(
    "/business/payments/{payment_id}",
    summary="Get payment by ID",
    description="Retrieve a single payment by its ID.",
    responses={
        200: {"description": "Payment retrieved successfully"},
        404: {"model": ErrorResponseModel},
        500: {"model": ErrorResponseModel},
    },
)
def get_payment_by_id(
    payment_id: int = Path(..., gt=0),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """
    Fetch one payment by ID.
    """
    logger.info(f"Fetching payment #{payment_id}")

    try:
        payment = financial_service.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundException(payment_id=payment_id)

        return {
            "success": True,
            "message": f"Payment #{payment_id} retrieved",
            "data": {
                "payment_id": getattr(payment, "payment_id", None),
                "payment_invoice_id": getattr(payment, "payment_invoice_id", None),
                "payment_amount": float(getattr(payment, "payment_amount", 0) or 0),
                "payment_method": getattr(payment, "payment_method", None),
                "payment_status": getattr(payment, "payment_status", None),
                "payment_reference": getattr(payment, "payment_reference", None),
                "payment_notes": getattr(payment, "payment_notes", None),
                "payment_type": getattr(payment, "payment_type", None),
                "payment_created_at": (
                    payment.payment_created_at.isoformat()
                    if getattr(payment, "payment_created_at", None)
                    else None
                ),
                "payment_updated_at": (
                    payment.payment_updated_at.isoformat()
                    if getattr(payment, "payment_updated_at", None)
                    else None
                ),
            },
        }

    except PaymentNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch payment {payment_id}: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})


# ==================== Deposit Endpoints ====================


@business_router.post(
    "/business/deposits",
    status_code=status.HTTP_201_CREATED,
    summary="Create deposit",
    description="Create a deposit against a cart or invoice.",
    responses={
        201: {"description": "Deposit created successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True, include_409=True),
    },
)
def create_deposit(
    deposit: Deposit_API = Body(...),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Create a deposit."""
    logger.info(
        f"Creating deposit - cart:{deposit.deposit_cart_id}, "
        f"amount:{deposit.deposit_amount}"
    )

    try:
        created = financial_service.create_deposit(deposit)
        return {
            "success": True,
            "message": "Deposit created successfully",
            "data": {
                "deposit_id": getattr(created, "deposit_id", None),
                "deposit_amount": float(getattr(created, "deposit_amount", 0) or 0),
                "deposit_method": getattr(created, "deposit_method", None),
                "deposit_cart_id": getattr(created, "deposit_cart_id", None),
                "deposit_invoice_id": getattr(created, "deposit_invoice_id", None),
            },
        }
    except PaymentCreationFailedException:
        raise
    except Exception as e:
        logger.error(f"Failed to create deposit: {e}")
        raise PaymentCreationFailedException(error=str(e))


@business_router.get(
    "/business/deposits",
    summary="List deposits",
    responses={200: {"description": "Deposits retrieved successfully"}},
)
def list_deposits(
    cart_id: Optional[int] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """List deposits."""
    try:
        deposits = financial_service.get_deposits(cart_id, offset, limit) or []
        return {
            "success": True,
            "message": f"Retrieved {len(deposits)} deposits",
            "data": [
                {
                    "deposit_id": getattr(d, "deposit_id", None),
                    "deposit_amount": float(getattr(d, "deposit_amount", 0) or 0),
                    "deposit_method": getattr(d, "deposit_method", None),
                    "deposit_cart_id": getattr(d, "deposit_cart_id", None),
                    "deposit_invoice_id": getattr(d, "deposit_invoice_id", None),
                }
                for d in deposits
            ],
        }
    except Exception as e:
        logger.error(f"Failed to list deposits: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})


@business_router.get(
    "/business/deposits/{deposit_id}",
    summary="Get deposit by ID",
    responses={
        200: {"description": "Deposit retrieved successfully"},
        404: {"model": ErrorResponseModel},
    },
)
def get_deposit_by_id(
    deposit_id: int = Path(..., gt=0),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Fetch one deposit."""
    try:
        deposit = financial_service.get_deposit_by_id(deposit_id)
        if not deposit:
            raise FinancialItemNotFoundException(
                details={"deposit_id": deposit_id}
            )
        return {
            "success": True,
            "data": {
                "deposit_id": getattr(deposit, "deposit_id", None),
                "deposit_amount": float(getattr(deposit, "deposit_amount", 0) or 0),
                "deposit_method": getattr(deposit, "deposit_method", None),
                "deposit_cart_id": getattr(deposit, "deposit_cart_id", None),
                "deposit_invoice_id": getattr(deposit, "deposit_invoice_id", None),
            },
        }
    except FinancialItemNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch deposit {deposit_id}: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})


# ==================== Fee Endpoints ====================


@business_router.post(
    "/business/fees",
    status_code=status.HTTP_201_CREATED,
    summary="Create additional fee",
    responses={
        201: {"description": "Fee created successfully"},
        400: {"model": ErrorResponseModel},
    },
)
def create_fee(
    fee: AdditionalFee_API = Body(...),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Create an additional fee."""
    try:
        created = financial_service.create_fee(fee)
        return {
            "success": True,
            "message": "Fee created successfully",
            "data": {
                "additional_fee_id": getattr(created, "additional_fee_id", None),
                "additional_fee_name": getattr(created, "additional_fee_name", None),
                "additional_fee_amount": float(
                    getattr(created, "additional_fee_amount", 0) or 0
                ),
            },
        }
    except Exception as e:
        logger.error(f"Failed to create fee: {e}")
        raise PaymentCreationFailedException(error=str(e))


@business_router.get(
    "/business/fees",
    summary="List fees",
    responses={200: {"description": "Fees retrieved successfully"}},
)
def list_fees(
    provider_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """List additional fees."""
    try:
        fees = financial_service.get_fees(provider_id, user_id, offset, limit) or []
        return {
            "success": True,
            "message": f"Retrieved {len(fees)} fees",
            "data": [
                {
                    "additional_fee_id": getattr(f, "additional_fee_id", None),
                    "additional_fee_name": getattr(f, "additional_fee_name", None),
                    "additional_fee_amount": float(
                        getattr(f, "additional_fee_amount", 0) or 0
                    ),
                    "additional_fee_on_provider_id": getattr(
                        f, "additional_fee_on_provider_id", None
                    ),
                }
                for f in fees
            ],
        }
    except Exception as e:
        logger.error(f"Failed to list fees: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})


@business_router.get(
    "/business/fees/{fee_id}",
    summary="Get fee by ID",
    responses={
        200: {"description": "Fee retrieved successfully"},
        404: {"model": ErrorResponseModel},
    },
)
def get_fee_by_id(
    fee_id: int = Path(..., gt=0),
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Fetch one fee."""
    try:
        fee = financial_service.get_fee_by_id(fee_id)
        if not fee:
            raise FinancialItemNotFoundException(details={"fee_id": fee_id})
        return {
            "success": True,
            "data": {
                "additional_fee_id": getattr(fee, "additional_fee_id", None),
                "additional_fee_name": getattr(fee, "additional_fee_name", None),
                "additional_fee_amount": float(
                    getattr(fee, "additional_fee_amount", 0) or 0
                ),
            },
        }
    except FinancialItemNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch fee {fee_id}: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})


# ==================== Legacy Compatibility ====================


@business_router.post(
    "/business/payment",
    status_code=status.HTTP_201_CREATED,
    summary="Add financial item (legacy)",
    description=(
        "Legacy wrapper. Prefer `/business/payments` for payments, "
        "`/business/deposits` for deposits, and `/business/fees` for fees."
    ),
    deprecated=True,
    responses={
        201: {"description": "Financial item created successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True, include_409=True),
    },
)
def add_payment_legacy(
    payment: Optional[Payment_API] = None,
    deposit: Optional[Deposit_API] = None,
    fee: Optional[AdditionalFee_API] = None,
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Legacy: adds a payment, deposit, or fee based on which body is sent."""
    if not payment and not deposit and not fee:
        raise PaymentCreationFailedException(
            error="At least one of payment, deposit, or fee must be provided"
        )

    item_type = "payment" if payment else "deposit" if deposit else "fee"
    logger.info(f"Legacy financial item creation - type: {item_type}")

    try:
        result = financial_service.create_financial_item(payment, deposit, fee)
        return result
    except Exception as e:
        logger.error(f"Failed to add financial item via legacy endpoint: {e}")
        raise PaymentCreationFailedException(
            error=str(e),
            details={"item_type": item_type},
        )


@business_router.get(
    "/business/doc/{supplier_id}/{person_id}/{client_id}/{seller_id}/"
    "{cart_id}/{order_id}/{deposit_id}/{invoice_id}/{offset}/{limit}",
    summary="Get financial documents (legacy)",
    deprecated=True,
    responses={
        200: {"description": "Financial documents retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True, include_403=False),
    },
)
def get_finances(
    supplier_id: int,
    person_id: int,
    client_id: int,
    seller_id: int,
    cart_id: int,
    order_id: int,
    deposit_id: int,
    invoice_id: int,
    offset: int,
    limit: int,
    financial_service: FinancialService = Depends(get_financial_service),
):
    """Legacy: fetch financial documents with path-based filters (use 0 to skip)."""
    actual_limit = min(limit, 100)
    logger.info(f"Legacy financial doc fetch - offset:{offset}, limit:{actual_limit}")

    try:
        result = financial_service.get_financial_items(
            supplier_id if supplier_id > 0 else None,
            person_id if person_id > 0 else None,
            client_id if client_id > 0 else None,
            seller_id if seller_id > 0 else None,
            cart_id if cart_id > 0 else None,
            order_id if order_id > 0 else None,
            deposit_id if deposit_id > 0 else None,
            invoice_id if invoice_id > 0 else None,
            offset,
            actual_limit,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to fetch financial documents: {e}")
        raise FinancialItemNotFoundException(details={"error": str(e)})