# routers/invoice_router.py
"""
Invoice router for managing invoices.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status, Path
from typing import Any, Dict, Optional, List
import logging

from core.models.api_models import (
    Invoice_API, InvoiceUpdate_API, InvoiceFilterParams,
    InvoiceResponse_API, InvoiceStatus
)
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.finance_exceptions import (
    InvoiceNotFoundException,
    InvoiceCreationFailedException,
    InvoiceUpdateFailedException,
)
from services.invoice_service import InvoiceService

from core.logging_config import get_logger

logger = get_logger(__name__)


invoice_router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"]
)


def get_invoice_service() -> InvoiceService:
    """Dependency to get InvoiceService instance."""
    return InvoiceService()


# ==================== CREATE ====================

@invoice_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Invoice_API,
    summary="Create invoice",
    description="Create a new invoice",
    responses={
        201: {"description": "Invoice created successfully"},
        400: {"model": ErrorResponseModel, "description": "Bad request"},
        404: {"model": ErrorResponseModel, "description": "Not found"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"},
        **get_crud_error_responses(include_404=True, include_409=True)
    }
)
def create_invoice(
    invoice: Invoice_API,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Create a new invoice.
    
    - **invoice**: Invoice data
    """
    logger.info(f"Creating invoice for cart: {invoice.invoice_cart_id}")
    return invoice_service.create_invoice(invoice)


@invoice_router.post(
    "/from-cart/{cart_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=Invoice_API,
    summary="Create invoice from cart",
    description="Create an invoice from an existing cart",
    responses={
        201: {"description": "Invoice created successfully"},
        404: {"model": ErrorResponseModel, "description": "Cart not found"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"}
    }
)
def create_invoice_from_cart(
    cart_id: int = Path(..., gt=0, description="Cart ID"),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Create an invoice from an existing cart.
    
    - **cart_id**: ID of the cart to create invoice from
    """
    logger.info(f"Creating invoice from cart: {cart_id}")
    return invoice_service.create_invoice_from_cart(cart_id)


# ==================== READ ====================

@invoice_router.get(
    "",
    # response_model=Dict[str, Any],
    summary="Get invoices",
    description="Get invoices with filters and pagination",
    responses={
        200: {"description": "Invoices retrieved successfully"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"}
    }
)
def get_invoices(
    status_: Optional[InvoiceStatus] = Query(None, alias="status", description="Filter by status"),
    type_: Optional[str] = Query(None, alias="type", description="Filter by type"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    cart_id: Optional[int] = Query(None, description="Filter by cart ID"),
    order_id: Optional[int] = Query(None, description="Filter by order ID"),
    provider_id: Optional[int] = Query(None, description="Filter by provider ID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Records per page"),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Get invoices with filters and pagination.
    
    - **status**: Filter by invoice status
    - **type**: Filter by invoice type
    - **date_from**: Filter invoices from this date
    - **date_to**: Filter invoices to this date
    - **cart_id**: Filter by cart ID
    - **order_id**: Filter by order ID
    - **provider_id**: Filter by provider ID
    - **offset**: Pagination offset
    - **limit**: Records per page
    """
    filters = InvoiceFilterParams(
        invoice_status=status_,
        invoice_type=type_,
        date_from=date_from,
        date_to=date_to,
        cart_id=cart_id,
        order_id=order_id,
        provider_id=provider_id,
        offset=offset,
        limit=limit
    )
    
    logger.info(f"Fetching invoices with filters")
    return invoice_service.get_invoices(filters)


@invoice_router.get(
    "/{invoice_id}",
    # response_model=InvoiceResponse_API,
    summary="Get invoice by ID",
    description="Get a specific invoice with all related data",
    responses={
        200: {"description": "Invoice retrieved successfully"},
        404: {"model": ErrorResponseModel, "description": "Invoice not found"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"}
    }
)
def get_invoice_by_id(
    invoice_id: int = Path(..., gt=0, description="Invoice ID"),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Get a specific invoice by ID with all related data.
    
    - **invoice_id**: ID of the invoice to retrieve
    """
    logger.info(f"Fetching invoice: {invoice_id}")
    return invoice_service.get_invoice_summary(invoice_id)


@invoice_router.get(
    "/{invoice_id}/summary",
    response_model=Dict[str, Any],
    summary="Get invoice summary",
    description="Get invoice summary with payments, deliveries, and fees",
    responses={
        200: {"description": "Invoice summary retrieved successfully"},
        404: {"model": ErrorResponseModel, "description": "Invoice not found"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"}
    }
)
def get_invoice_summary(
    invoice_id: int = Path(..., gt=0, description="Invoice ID"),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Get invoice summary with payments, deliveries, and fees.
    
    - **invoice_id**: ID of the invoice to summarize
    """
    logger.info(f"Getting summary for invoice: {invoice_id}")
    return invoice_service.get_invoice_summary(invoice_id)


# ==================== UPDATE ====================

@invoice_router.patch(
    "/{invoice_id}",
    response_model=Invoice_API,
    summary="Update invoice",
    description="Update an existing invoice",
    responses={
        200: {"description": "Invoice updated successfully"},
        400: {"model": ErrorResponseModel, "description": "Bad request"},
        404: {"model": ErrorResponseModel, "description": "Invoice not found"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"}
    }
)
def update_invoice(
    invoice_id: int = Path(..., gt=0, description="Invoice ID"),
    update_data: InvoiceUpdate_API = None,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Update an existing invoice.
    
    - **invoice_id**: ID of the invoice to update
    - **update_data**: Fields to update
    """
    logger.info(f"Updating invoice: {invoice_id}")
    return invoice_service.update_invoice(invoice_id, update_data)




# ==================== DELETE ====================

@invoice_router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete invoice",
    description="Delete an invoice",
    responses={
        204: {"description": "Invoice deleted successfully"},
        400: {"model": ErrorResponseModel, "description": "Cannot delete invoice"},
        404: {"model": ErrorResponseModel, "description": "Invoice not found"},
        500: {"model": ErrorResponseModel, "description": "Internal server error"}
    }
)
def delete_invoice(
    invoice_id: int = Path(..., gt=0, description="Invoice ID"),
    force: bool = Query(False, description="Force deletion"),
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """
    Delete an invoice.
    
    - **invoice_id**: ID of the invoice to delete
    - **force**: Force deletion even if not draft
    """
    logger.info(f"Deleting invoice: {invoice_id} (force: {force})")
    result = invoice_service.delete_invoice(invoice_id, force)
    
    if result:
        return {"message": f"Invoice {invoice_id} deleted successfully"}
    return None