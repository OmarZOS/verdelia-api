# routers/document_router.py
"""
Document router for generating invoices, receipts, and PDF documents.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse, Response
from typing import Optional
import logging

from core.exceptions.specific.document_exceptions import DocumentGenerationFailedException
from core.exceptions.specific.finance_exceptions import InvoiceNotFoundException, ReceiptNotFoundException
from core.response_models import (
    SuccessResponseModel,
    ErrorResponseModel,
    get_crud_error_responses
)
from core.exceptions.specific.cart_exceptions import (
    CartNotFoundException,
)
from services.document_service import DocumentService

from core.logging_config import get_logger

logger = get_logger(__name__)


document_router = APIRouter(
    # tags=["documents"],
    # prefix="/api/documents"
)


def get_document_service() -> DocumentService:
    """Dependency to get DocumentService instance"""
    return DocumentService()


# ==================== Invoice HTML Endpoints ====================

@document_router.get(
    "/cart/invoice/{provider_id}/{seller_id}/{cart_id}/{client_id}/{person_id}",
    response_class=HTMLResponse,
    summary="Generate invoice HTML",
    description="Generate invoice HTML for a cart",
    responses={
        200: {
            "description": "Invoice HTML generated successfully",
            "content": {
                "text/html": {
                    "schema": {
                        "type": "string",
                        "description": "HTML invoice document"
                    }
                }
            }
        },
        404: {
            "description": "Cart not found",
            "model": ErrorResponseModel
        },
        500: {
            "description": "Document generation failed",
            "model": ErrorResponseModel
        }
    }
)
def fetch_cart_invoice(
    provider_id: int,  # Path parameter - NO Query()
    seller_id: int,    # Path parameter - NO Query()
    cart_id: int,      # Path parameter - NO Query()
    client_id: int,    # Path parameter - NO Query()
    person_id: int,    # Path parameter - NO Query()
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Generate invoice HTML for a cart.
    
    - **provider_id**: Filter by provider ID (path parameter)
    - **seller_id**: Filter by seller ID (path parameter)
    - **cart_id**: Filter by cart ID (path parameter)
    - **client_id**: Filter by client ID (path parameter)
    - **person_id**: Filter by person ID (path parameter)
    
    Returns:
        HTMLResponse: Invoice HTML document
    """
    logger.info(f"Generating invoice HTML - provider:{provider_id}, seller:{seller_id}, cart:{cart_id}, client:{client_id}, person:{person_id}")
    
    try:
        html_content = document_service.generate_invoice_html(
            provider_id, seller_id, cart_id, client_id, person_id
        )
        
        if not html_content:
            raise CartNotFoundException(cart_id=cart_id if cart_id > 0 else None)
        
        return HTMLResponse(
            content=html_content,
            status_code=200,
            headers={
                "Content-Type": "text/html",
                "X-Document-Type": "invoice"
            }
        )
        
    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate invoice HTML: {e}")
        raise DocumentGenerationFailedException(
            document_type="invoice",
            format="html",
            error=str(e),
            details={
                "provider_id": provider_id,
                "seller_id": seller_id,
                "cart_id": cart_id
            }
        )


# ==================== Receipt HTML Endpoints ====================

@document_router.get(
    "/cart/receipt/{provider_id}/{seller_id}/{cart_id}/{client_id}/{person_id}",
    response_class=HTMLResponse,
    summary="Generate receipt HTML",
    description="Generate receipt HTML for a cart",
    responses={
        200: {
            "description": "Receipt HTML generated successfully",
            "content": {
                "text/html": {
                    "schema": {
                        "type": "string",
                        "description": "HTML receipt document"
                    }
                }
            }
        },
        404: {
            "description": "Cart not found",
            "model": ErrorResponseModel
        },
        500: {
            "description": "Document generation failed",
            "model": ErrorResponseModel
        }
    }
)
def fetch_cart_receipt(
    provider_id: int,  # Path parameter - NO Query()
    seller_id: int,    # Path parameter - NO Query()
    cart_id: int,      # Path parameter - NO Query()
    client_id: int,    # Path parameter - NO Query()
    person_id: int,    # Path parameter - NO Query()
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Generate receipt HTML for a cart.
    
    - **provider_id**: Filter by provider ID (path parameter)
    - **seller_id**: Filter by seller ID (path parameter)
    - **cart_id**: Filter by cart ID (path parameter)
    - **client_id**: Filter by client ID (path parameter)
    - **person_id**: Filter by person ID (path parameter)
    
    Returns:
        HTMLResponse: Receipt HTML document
    """
    logger.info(f"Generating receipt HTML - provider:{provider_id}, seller:{seller_id}, cart:{cart_id}, client:{client_id}, person:{person_id}")
    
    try:
        html_content = document_service.generate_receipt_html(
            provider_id, seller_id, cart_id, client_id, person_id
        )
        
        if not html_content:
            raise CartNotFoundException(cart_id=cart_id if cart_id > 0 else None)
        
        return HTMLResponse(
            content=html_content,
            status_code=200,
            headers={
                "Content-Type": "text/html",
                "X-Document-Type": "receipt"
            }
        )
        
    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate receipt HTML: {e}")
        raise DocumentGenerationFailedException(
            document_type="receipt",
            format="html",
            error=str(e),
            details={
                "provider_id": provider_id,
                "seller_id": seller_id,
                "cart_id": cart_id
            }
        )


# ==================== Invoice PDF Endpoints ====================

@document_router.get(
    "/cart/invoice/pdf",
    summary="Generate invoice PDF",
    description="Generate invoice PDF for a cart",
    responses={
        200: {
            "description": "Invoice PDF generated successfully",
            "content": {
                "application/pdf": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                        "description": "PDF invoice document"
                    }
                }
            }
        },
        404: {
            "description": "Cart not found",
            "model": ErrorResponseModel
        },
        500: {
            "description": "PDF generation failed",
            "model": ErrorResponseModel
        }
    }
)
def fetch_cart_invoice_pdf(
    provider_id: int = Query(0, description="Provider ID"),
    seller_id: int = Query(0, description="Seller ID"),
    cart_id: int = Query(0, description="Cart ID"),
    client_id: int = Query(0, description="Client ID"),
    person_id: int = Query(0, description="Person ID"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Generate invoice PDF for a cart.
    
    - **provider_id**: Provider ID (query parameter)
    - **seller_id**: Seller ID (query parameter)
    - **cart_id**: Cart ID (query parameter)
    - **client_id**: Client ID (query parameter)
    - **person_id**: Person ID (query parameter)
    
    Returns:
        Response: PDF file download
    """
    logger.info(f"Generating invoice PDF - provider:{provider_id}, seller:{seller_id}, cart:{cart_id}")
    
    try:
        pdf_content = document_service.generate_invoice_pdf(
            provider_id, seller_id, cart_id, client_id, person_id
        )
        
        if not pdf_content:
            raise CartNotFoundException(cart_id=cart_id if cart_id > 0 else None)
        
        # Generate filename
        filename = f"invoice_cart_{cart_id if cart_id > 0 else provider_id if provider_id > 0 else seller_id}.pdf"
        
        return Response(
            content=pdf_content,
            status_code=200,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf",
                "X-Document-Type": "invoice"
            }
        )
        
    except CartNotFoundException:
        raise
    except ValueError as e:
        logger.error(f"Value error generating invoice PDF: {e}")
        raise InvoiceNotFoundException(
            invoice_id=cart_id if cart_id > 0 else None,
            details={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to generate invoice PDF: {e}")
        raise DocumentGenerationFailedException(
            document_type="invoice",
            format="pdf",
            error=str(e),
            details={
                "provider_id": provider_id,
                "seller_id": seller_id,
                "cart_id": cart_id
            }
        )


# ==================== Receipt PDF Endpoints ====================

@document_router.get(
    "/cart/receipt/pdf",
    summary="Generate receipt PDF",
    description="Generate receipt PDF for a cart",
    responses={
        200: {
            "description": "Receipt PDF generated successfully",
            "content": {
                "application/pdf": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                        "description": "PDF receipt document"
                    }
                }
            }
        },
        404: {
            "description": "Cart not found",
            "model": ErrorResponseModel
        },
        500: {
            "description": "PDF generation failed",
            "model": ErrorResponseModel
        }
    }
)
def fetch_cart_receipt_pdf(
    provider_id: int = Query(0, description="Provider ID"),
    seller_id: int = Query(0, description="Seller ID"),
    cart_id: int = Query(0, description="Cart ID"),
    client_id: int = Query(0, description="Client ID"),
    person_id: int = Query(0, description="Person ID"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Generate receipt PDF for a cart.
    
    - **provider_id**: Provider ID (query parameter)
    - **seller_id**: Seller ID (query parameter)
    - **cart_id**: Cart ID (query parameter)
    - **client_id**: Client ID (query parameter)
    - **person_id**: Person ID (query parameter)
    
    Returns:
        Response: PDF file download
    """
    logger.info(f"Generating receipt PDF - provider:{provider_id}, seller:{seller_id}, cart:{cart_id}")
    
    try:
        pdf_content = document_service.generate_receipt_pdf(
            provider_id, seller_id, cart_id, client_id, person_id
        )
        
        if not pdf_content:
            raise CartNotFoundException(cart_id=cart_id if cart_id > 0 else None)
        
        # Generate filename
        filename = f"receipt_cart_{cart_id if cart_id > 0 else provider_id if provider_id > 0 else seller_id}.pdf"
        
        return Response(
            content=pdf_content,
            status_code=200,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf",
                "X-Document-Type": "receipt"
            }
        )
        
    except CartNotFoundException:
        raise
    except ValueError as e:
        logger.error(f"Value error generating receipt PDF: {e}")
        raise ReceiptNotFoundException(
            receipt_id=cart_id if cart_id > 0 else None,
            details={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to generate receipt PDF: {e}")
        raise DocumentGenerationFailedException(
            document_type="receipt",
            format="pdf",
            error=str(e),
            details={
                "provider_id": provider_id,
                "seller_id": seller_id,
                "cart_id": cart_id
            }
        )


# ==================== Cart Data Endpoint ====================

@document_router.get(
    "/cart/data",
    # response_model=SuccessResponseModel,
    summary="Get cart data",
    description="Get cart data as JSON for debugging or API integration",
    responses={
        200: {
            "description": "Cart data retrieved successfully",
            "model": SuccessResponseModel
        },
        404: {
            "description": "Cart not found",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True, include_403=False)
    }
)
def get_cart_data(
    provider_id: int = Query(0, description="Provider ID"),
    seller_id: int = Query(0, description="Seller ID"),
    cart_id: int = Query(0, description="Cart ID"),
    client_id: int = Query(0, description="Client ID"),
    person_id: int = Query(0, description="Person ID"),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    Get cart data as JSON for debugging or API integration.
    
    - **provider_id**: Provider ID (query parameter)
    - **seller_id**: Seller ID (query parameter)
    - **cart_id**: Cart ID (query parameter)
    - **client_id**: Client ID (query parameter)
    - **person_id**: Person ID (query parameter)
    
    Returns:
        Cart data in JSON format
    """
    logger.info(f"Fetching cart data - provider:{provider_id}, seller:{seller_id}, cart:{cart_id}")
    
    try:
        cart_data = document_service.get_cart_for_document(
            provider_id, seller_id, cart_id, client_id, person_id
        )
        
        if not cart_data:
            raise CartNotFoundException(cart_id=cart_id if cart_id > 0 else None)
        
        return cart_data
        
    except CartNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch cart data: {e}")
        raise DocumentGenerationFailedException(
            document_type="cart_data",
            format="json",
            error=str(e)
        )