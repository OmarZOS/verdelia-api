# services/invoice_service.py
"""
Invoice service for managing invoices, payments, and financial tracking.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import logging
import random
import string

from repositories.invoice_repository import InvoiceRepository
from core.models.api_models import (
    Invoice_API, InvoiceStatus, InvoiceType, 
    InvoiceUpdate_API, InvoiceFilterParams
)
from core.models.models import Invoice, Payment, Cart, PlacedOrder, Delivery, AdditionalFee
from core.exceptions.specific.finance_exceptions import (
    InvoiceNotFoundException,
    InvoiceCreationFailedException,
    InvoiceUpdateFailedException,
)

from core.logging_config import get_logger

logger = get_logger(__name__)



class InvoiceService:
    """Service for invoice operations"""
    
    def __init__(self):
        self.invoice_repo = InvoiceRepository()
    
    # ==================== CREATE ====================
    
    def create_invoice(self, invoice_data: Invoice_API) -> Invoice:
        """
        Create a new invoice.
        
        Args:
            invoice_data: Invoice data
            
        Returns:
            Created Invoice
            
        Raises:
            InvoiceCreationFailedException: If creation fails
        """
        logger.info(f"Creating invoice for cart: {invoice_data.invoice_cart_id}")
        
        try:
            # Generate invoice number if not provided
            invoice_number = invoice_data.invoice_number
            if not invoice_number:
                invoice_number = self._generate_invoice_number()
            
            # Build invoice object
            invoice = Invoice(
                invoice_number=invoice_number,
                invoice_total_amount=invoice_data.invoice_total_amount,
                invoice_status=invoice_data.invoice_status.value,
                invoice_type=invoice_data.invoice_type.value,
                invoice_issue_date=invoice_data.invoice_issue_date or date.today(),
                invoice_due_date=invoice_data.invoice_due_date,
                invoice_notes=invoice_data.invoice_notes,
                invoice_tax_applied=1 if invoice_data.invoice_tax_applied else 0,
                invoice_created_at=datetime.now(),
                invoice_updated_at=datetime.now()
            )
            
            # Save invoice using repository
            created_invoice = self.invoice_repo.create(invoice)
            
            # Link to cart or order if provided
            if invoice_data.invoice_cart_id:
                self.invoice_repo.link_to_cart(created_invoice.invoice_id, invoice_data.invoice_cart_id)
            
            if invoice_data.invoice_order_id:
                self.invoice_repo.link_to_order(created_invoice.invoice_id, invoice_data.invoice_order_id)
            
            logger.info(f"Invoice created with ID: {created_invoice.invoice_id}")
            return created_invoice
            
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise InvoiceCreationFailedException(details=str(e))
    
    def create_invoice_from_cart(self, cart_id: int) -> Invoice:
        """
        Create an invoice from a cart.
        
        Args:
            cart_id: Cart ID
            
        Returns:
            Created Invoice
            
        Raises:
            InvoiceCreationFailedException: If creation fails
        """
        logger.info(f"Creating invoice from cart: {cart_id}")
        
        try:
            # Get cart and calculate total
            cart = self.invoice_repo.get_cart(cart_id)
            if not cart:
                raise InvoiceCreationFailedException(details="Cart not found")
            
            # Calculate totals from cart items
            total_amount = self._calculate_cart_total(cart)
            
            # Create invoice
            invoice_data = Invoice_API(
                invoice_total_amount=total_amount,
                invoice_status=InvoiceStatus.UNPAID,
                invoice_type=InvoiceType.INVOICE,
                invoice_issue_date=date.today(),
                invoice_due_date=date.today() + timedelta(days=30),
                invoice_notes=f"Invoice for cart #{cart_id}",
                invoice_cart_id=cart_id
            )
            
            return self.create_invoice(invoice_data)
            
        except Exception as e:
            logger.error(f"Failed to create invoice from cart: {e}")
            raise InvoiceCreationFailedException(details=str(e))
    
    # ==================== READ ====================
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get invoice by ID with related data.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice with related data or None
        """
        logger.debug(f"Fetching invoice: {invoice_id}")
        return self.invoice_repo.get_with_relations(invoice_id)
    
    def get_invoices(
        self,
        filters: Optional[InvoiceFilterParams] = None
    ) -> Dict[str, Any]:
        """
        Get invoices with filters.
        
        Args:
            filters: Filter parameters
            
        Returns:
            Dict with invoices, total count, pagination info
        """
        logger.info(f"Fetching invoices with filters: {filters}")
        
        if filters is None:
            filters = InvoiceFilterParams()
        
        invoices = self.invoice_repo.get_with_filters(
            status=filters.invoice_status.value if filters.invoice_status else None,
            type_=filters.invoice_type if filters.invoice_type else None,
            date_from=filters.date_from,
            date_to=filters.date_to,
            cart_id=filters.cart_id,
            provider_id=filters.provider_id,
            order_id=filters.order_id,
            offset=filters.offset,
            limit=filters.limit
        )
        
        
        return invoices
    
    def get_invoice_summary(self, invoice_id: int) -> Dict[str, Any]:
        """
        Get invoice summary with payments, deliveries, and fees.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice summary data
        """
        logger.info(f"Getting summary for invoice: {invoice_id}")
        
        invoice = self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise InvoiceNotFoundException(invoice_id=invoice_id)
        
        
        return invoice
    
    # ==================== UPDATE ====================
    
    
    def update_invoice_status(
        self,
        invoice_id: int,
        new_status: InvoiceStatus
    ) -> Invoice:
        """
        Update invoice status.
        
        Args:
            invoice_id: Invoice ID
            new_status: New status
            
        Returns:
            Updated Invoice
        """
        update_data = InvoiceUpdate_API(invoice_status=new_status)
        return self.update_invoice(invoice_id, update_data)
    
    # ==================== DELETE ====================
    
    
    # ==================== HELPER METHODS ====================
    
    def _generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        prefix = "INV"
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=6))
        
        return f"{prefix}-{timestamp}-{random_part}"
    
    def _calculate_cart_total(self, cart) -> float:
        """Calculate cart total including items and fees."""
        total = 0.0
        
        # Sum ordered items
        if hasattr(cart, 'ordered_items'):
            for item in cart.ordered_items:
                total += (float(item.unit_price or 0) * float(item.ordered_quantity or 0))
        
        # Sum ordered services
        if hasattr(cart, 'ordered_services'):
            for service in cart.ordered_services:
                total += float(service.ordered_service_total_price or 0)
        
        return total
    