# repositories/invoice_repository.py
"""
Invoice repository for database operations.
Following the same pattern as cart_repository.py
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime
from sqlalchemy.orm import joinedload, sessionmaker, Session
from sqlalchemy import select, delete, func, desc, and_, or_

from core.models.models import (
    Invoice, Payment, Cart, PlacedOrder, Delivery, AdditionalFee
)
import storage.storage_broker as storage_broker
from core.exceptions.handler import APIException
from core.messages import *
import logging

from core.logging_config import get_logger

logger = get_logger(__name__)



class InvoiceRepository:
    """Repository for Invoice-related database operations"""
    
    # ==================== CREATE ====================
    
    def create(self, invoice: Invoice) -> Invoice:
        """Create a new invoice."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(invoice)
    
    def link_to_cart(self, invoice_id: int, cart_id: int) -> bool:
        """Link invoice to cart."""
        try:
            with storage_broker.session_scope() as session:
                cart = session.query(Cart).filter(Cart.cart_id == cart_id).first()
                if cart:
                    cart.cart_invoice = invoice_id
                    session.flush()
                    logger.info(f"Invoice {invoice_id} linked to cart {cart_id}")
                    return True
                logger.warning(f"Cart {cart_id} not found for linking to invoice {invoice_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to link invoice {invoice_id} to cart {cart_id}: {e}")
            return False
    
    def link_to_order(self, invoice_id: int, order_id: int) -> bool:
        """Link invoice to order."""
        try:
            with storage_broker.session_scope() as session:
                order = session.query(PlacedOrder).filter(
                    PlacedOrder.id_placed_order == order_id
                ).first()
                if order:
                    order.placed_order_invoice = invoice_id
                    session.flush()
                    logger.info(f"Invoice {invoice_id} linked to order {order_id}")
                    return True
                logger.warning(f"Order {order_id} not found for linking to invoice {invoice_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to link invoice {invoice_id} to order {order_id}: {e}")
            return False
    
    # ==================== READ ====================
    
    def get(self, invoice_id: int, eager_load: bool = True) -> Optional[Invoice]:
        """Get invoice by ID with optional eager loading."""
        if eager_load:
            eager_fields = [
                Invoice.payment,
                Invoice.placed_order,
                Invoice.cart,
                Invoice.delivery,
                Invoice.additional_fee
            ]
        else:
            eager_fields = []
        
        records = storage_broker.get(
            Invoice,
            {Invoice.invoice_id: invoice_id},
            [],
            eager_fields
        )
        return records[0] if records else None
    
    def get_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        records = storage_broker.get(
            Invoice,
            {Invoice.invoice_number: invoice_number},
            [],
            []
        )
        return records[0] if records else None
    
    def get_with_relations(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice with all related data."""
        return self.get(invoice_id, eager_load=True)
    
    def get_with_filters(
        self,
        status: Optional[str] = None,
        type_: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        cart_id: Optional[int] = None,
        provider_id: Optional[int] = None,
        order_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """Get invoices with filters."""
        # Build conditions
        conditions = {}
        
        if status:
            conditions[Invoice.invoice_status] = status
        if type_:
            conditions[Invoice.invoice_type] = type_

        
        # For date filters, we need to use extra_filters
        extra_filters = []
        
        if date_from:
            extra_filters.append(Invoice.invoice_issue_date >= date_from)
        if date_to:
            extra_filters.append(Invoice.invoice_issue_date <= date_to)
        
        # For cart_id and order_id, we need joins
        eager_fields = [
            Invoice.payment,
            Invoice.placed_order,
            Invoice.cart,
            Invoice.delivery,
            Invoice.additional_fee
        ]
        
        invoices = storage_broker.get(
            Invoice,
            conditions,
            extra_filters,
            eager_fields,
            offset=offset,
            limit=limit,
            # order_by=desc(Invoice.invoice_created_at)
        )
        
        # Apply cart_id and order_id filters (since storage_broker doesn't support join filters directly)
        if cart_id or order_id or provider_id:
            filtered_invoices = []
            for invoice in invoices:
                if cart_id and invoice.cart and invoice.cart.cart_id == cart_id:
                    filtered_invoices.append(invoice)
                
                if provider_id and len(invoice.cart)>0 and invoice.cart[0] and invoice.cart[0].cart_product_provider_id == provider_id:
                    filtered_invoices.append(invoice)
                elif order_id and invoice.placed_order and invoice.placed_order.id_placed_order == order_id:
                    filtered_invoices.append(invoice)
            return filtered_invoices
        
        return invoices
    
    def count_with_filters(
        self,
        status: Optional[str] = None,
        type_: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        cart_id: Optional[int] = None,
        order_id: Optional[int] = None,
        provider_id: Optional[int] = None
    ) -> int:
        """Count invoices with filters."""
        conditions = {}
        
        if status:
            conditions[Invoice.invoice_status] = status
        if type_:
            conditions[Invoice.invoice_type] = type_
        
        extra_filters = []
        
        if date_from:
            extra_filters.append(Invoice.invoice_issue_date >= date_from)
        if date_to:
            extra_filters.append(Invoice.invoice_issue_date <= date_to)
        
        total = storage_broker.count(Invoice, conditions, extra_filters)
        
        # Apply cart_id and order_id filters
        if cart_id or order_id or provider_id:
            invoices = storage_broker.get(Invoice, conditions, extra_filters, [], limit=1000)
            filtered_count = 0
            for invoice in invoices:
                if cart_id and invoice.cart and invoice.cart.cart_id == cart_id:
                    filtered_count += 1
                elif order_id and invoice.placed_order and invoice.placed_order.id_placed_order == order_id:
                    filtered_count += 1
                elif provider_id and invoice.cart and invoice.cart.cart_product_provider_id == provider_id:
                    filtered_count += 1
            return filtered_count
        
        return total
    
    def get_invoice_summary_data(self, invoice_id: int) -> Dict[str, Any]:
        """Get invoice summary with payments, deliveries, and fees."""
        try:
            with storage_broker.session_scope() as session:
                invoice = session.query(Invoice).filter(
                    Invoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    return None
                
                # Get payments
                payments = session.query(Payment).filter(
                    Payment.payment_invoice_id == invoice_id
                ).order_by(desc(Payment.payment_created_at)).all()
                
                # Get deliveries
                deliveries = session.query(Delivery).filter(
                    Delivery.delivery_invoice_ref == invoice_id
                ).all()
                
                # Get additional fees
                fees = session.query(AdditionalFee).filter(
                    AdditionalFee.additional_fee_invoice == invoice_id
                ).all()
                
                # Get cart if exists
                cart = None
                if invoice.cart:
                    cart = session.query(Cart).filter(
                        Cart.cart_invoice == invoice_id
                    ).first()
                
                # Get order if exists
                order = None
                if invoice.placed_order:
                    order = session.query(PlacedOrder).filter(
                        PlacedOrder.placed_order_invoice == invoice_id
                    ).first()
                
                return {
                    "invoice": invoice,
                    "payments": payments,
                    "deliveries": deliveries,
                    "additional_fees": fees,
                    "cart": cart,
                    "order": order
                }
        except Exception as e:
            logger.error(f"Failed to get invoice summary for {invoice_id}: {e}")
            return None
    
    # ==================== UPDATE ====================
    
    def update(self, invoice_id: int, update_data: Dict[str, Any]) -> Invoice:
        """Update an invoice."""
        try:
            with storage_broker.session_scope() as session:
                invoice = session.query(Invoice).filter(
                    Invoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    raise APIException(
                        message=f"Invoice {invoice_id} not found",
                        error_code="INVOICE_NOT_FOUND",
                        status_code=404
                    )
                
                for key, value in update_data.items():
                    if hasattr(invoice, key):
                        setattr(invoice, key, value)
                
                invoice.invoice_updated_at = datetime.now()
                session.flush()
                session.refresh(invoice)
                
                logger.info(f"Invoice {invoice_id} updated successfully")
                return invoice
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to update invoice {invoice_id}: {e}")
            raise APIException(
                message=f"Failed to update invoice: {str(e)}",
                error_code="INVOICE_UPDATE_FAILED",
                status_code=500
            )
    
    def update_invoice_status(self, invoice_id: int, new_status: str) -> bool:
        """Update invoice status."""
        try:
            with storage_broker.session_scope() as session:
                invoice = session.query(Invoice).filter(
                    Invoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    logger.warning(f"Invoice {invoice_id} not found for status update")
                    return False
                
                invoice.invoice_status = new_status
                invoice.invoice_updated_at = datetime.now()
                session.flush()
                
                logger.info(f"Invoice {invoice_id} status updated to {new_status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update invoice {invoice_id} status: {e}")
            return False
    
    # ==================== DELETE ====================
    
    def delete(self, invoice_id: int) -> bool:
        """Delete an invoice by ID."""
        try:
            with storage_broker.session_scope() as session:
                invoice = session.query(Invoice).filter(
                    Invoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    logger.warning(f"Invoice {invoice_id} not found for deletion")
                    return False
                
                session.delete(invoice)
                session.flush()
                
                logger.info(f"Invoice {invoice_id} deleted")
                return True
        except Exception as e:
            logger.error(f"Failed to delete invoice {invoice_id}: {e}")
            return False
    
    def delete_relations(self, invoice_id: int) -> bool:
        """Delete all related records for an invoice."""
        try:
            with storage_broker.session_scope() as session:
                # Delete payments
                session.query(Payment).filter(
                    Payment.payment_invoice_id == invoice_id
                ).delete(synchronize_session=False)
                
                # Delete deliveries
                session.query(Delivery).filter(
                    Delivery.delivery_invoice_ref == invoice_id
                ).delete(synchronize_session=False)
                
                # Delete additional fees
                session.query(AdditionalFee).filter(
                    AdditionalFee.additional_fee_invoice == invoice_id
                ).delete(synchronize_session=False)
                
                session.flush()
                logger.info(f"All relations for invoice {invoice_id} deleted")
                return True
        except Exception as e:
            logger.error(f"Failed to delete relations for invoice {invoice_id}: {e}")
            return False
    
    def delete_invoice_sync(self, invoice: Invoice) -> bool:
        """Synchronously delete an invoice and all related records."""
        try:
            with storage_broker.session_scope() as session:
                # Merge invoice into session
                invoice_merged = session.merge(invoice)
                
                # Delete related payments
                session.query(Payment).filter(
                    Payment.payment_invoice_id == invoice_merged.invoice_id
                ).delete(synchronize_session=False)
                
                # Delete related deliveries
                session.query(Delivery).filter(
                    Delivery.delivery_invoice_ref == invoice_merged.invoice_id
                ).delete(synchronize_session=False)
                
                # Delete related additional fees
                session.query(AdditionalFee).filter(
                    AdditionalFee.additional_fee_invoice == invoice_merged.invoice_id
                ).delete(synchronize_session=False)
                
                # Now delete the invoice
                session.delete(invoice_merged)
                session.flush()
                
                logger.info(f"Invoice {invoice.invoice_id} deleted synchronously with all related records")
                return True
        except Exception as e:
            logger.error(f"Failed to delete invoice {invoice.invoice_id}: {e}")
            return False
    
    def delete_invoice_by_id_sync(self, invoice_id: int) -> bool:
        """Delete an invoice by ID synchronously."""
        try:
            with storage_broker.session_scope() as session:
                # Get invoice
                invoice = session.query(Invoice).filter(
                    Invoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    logger.warning(f"Invoice {invoice_id} not found for deletion")
                    return False
                
                # Delete related payments
                session.query(Payment).filter(
                    Payment.payment_invoice_id == invoice_id
                ).delete(synchronize_session=False)
                
                # Delete related deliveries
                session.query(Delivery).filter(
                    Delivery.delivery_invoice_ref == invoice_id
                ).delete(synchronize_session=False)
                
                # Delete related additional fees
                session.query(AdditionalFee).filter(
                    AdditionalFee.additional_fee_invoice == invoice_id
                ).delete(synchronize_session=False)
                
                # Delete the invoice
                session.delete(invoice)
                session.flush()
                
                logger.info(f"Invoice {invoice_id} deleted by ID synchronously")
                return True
        except Exception as e:
            logger.error(f"Failed to delete invoice {invoice_id}: {e}")
            return False
    
    # ==================== RELATED DATA ====================
    
    def get_payments(self, invoice_id: int) -> List[Payment]:
        """Get payments for an invoice."""
        try:
            with storage_broker.session_scope() as session:
                return session.query(Payment).filter(
                    Payment.payment_invoice_id == invoice_id
                ).order_by(desc(Payment.payment_created_at)).all()
        except Exception as e:
            logger.error(f"Failed to get payments for invoice {invoice_id}: {e}")
            return []
    
    def get_deliveries(self, invoice_id: int) -> List[Delivery]:
        """Get deliveries for an invoice."""
        try:
            with storage_broker.session_scope() as session:
                return session.query(Delivery).filter(
                    Delivery.delivery_invoice_ref == invoice_id
                ).all()
        except Exception as e:
            logger.error(f"Failed to get deliveries for invoice {invoice_id}: {e}")
            return []
    
    def get_fees(self, invoice_id: int) -> List[AdditionalFee]:
        """Get additional fees for an invoice."""
        try:
            with storage_broker.session_scope() as session:
                return session.query(AdditionalFee).filter(
                    AdditionalFee.additional_fee_invoice == invoice_id
                ).all()
        except Exception as e:
            logger.error(f"Failed to get fees for invoice {invoice_id}: {e}")
            return []
    
    def get_cart(self, cart_id: int) -> Optional[Cart]:
        """Get cart with related data."""
        try:
            with storage_broker.session_scope() as session:
                return session.query(Cart).filter(
                    Cart.cart_id == cart_id
                ).options(
                    joinedload(Cart.ordered_item),
                    joinedload(Cart.ordered_service)
                ).first()
        except Exception as e:
            logger.error(f"Failed to get cart {cart_id}: {e}")
            return None
    
    # ==================== STATISTICS ====================
    
    def count_invoices_by_status(self) -> Dict[str, int]:
        """Count invoices grouped by status."""
        try:
            with storage_broker.session_scope() as session:
                results = session.query(
                    Invoice.invoice_status,
                    func.count(Invoice.invoice_id)
                ).group_by(Invoice.invoice_status).all()
                
                return {status: count for status, count in results}
        except Exception as e:
            logger.error(f"Failed to count invoices by status: {e}")
            return {}
    
    def get_total_revenue(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> float:
        """Get total revenue from paid invoices."""
        try:
            with storage_broker.session_scope() as session:
                query = session.query(func.sum(Invoice.invoice_total_amount)).filter(
                    Invoice.invoice_status == 'paid'
                )
                
                if date_from:
                    query = query.filter(Invoice.invoice_issue_date >= date_from)
                if date_to:
                    query = query.filter(Invoice.invoice_issue_date <= date_to)
                
                return query.scalar() or 0.0
        except Exception as e:
            logger.error(f"Failed to get total revenue: {e}")
            return 0.0
    
    def get_pending_payments_total(self) -> float:
        """Get total amount of pending invoices."""
        try:
            with storage_broker.session_scope() as session:
                total = session.query(func.sum(Invoice.invoice_total_amount)).filter(
                    Invoice.invoice_status.in_(['unpaid', 'partially_paid'])
                ).scalar()
                return total or 0.0
        except Exception as e:
            logger.error(f"Failed to get pending payments total: {e}")
            return 0.0
    
    def get_overdue_invoices(self) -> List[Invoice]:
        """Get all overdue invoices."""
        try:
            with storage_broker.session_scope() as session:
                today = date.today()
                return session.query(Invoice).filter(
                    Invoice.invoice_due_date < today,
                    Invoice.invoice_status.in_(['unpaid', 'partially_paid'])
                ).all()
        except Exception as e:
            logger.error(f"Failed to get overdue invoices: {e}")
            return []