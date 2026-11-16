# repositories/financial_repository.py
from datetime import datetime
from typing import Optional, List, Tuple

from core.models.models import Invoice, Payment
import storage.storage_broker as storage_broker
from sqlalchemy import exists, select, delete, func, desc, and_, or_
from core.logging_config import get_logger

logger = get_logger(__name__)

class FinancialRepository:
    """Repository for financial document operations"""
    
    def create_invoice(self, invoice: Invoice) -> Invoice:
        """Create an invoice"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(invoice)

    
    
    def create_payment(self, payment: Payment) -> Payment:
        """Create a payment"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(payment)
    
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID"""
        records = storage_broker.get(Invoice, {Invoice.invoice_id: invoice_id}, [], [Invoice.payment])
        return records[0] if records else None

    def get_payment_by_invoice_and_status(
        self, invoice_id: int, status: str
    ) -> Optional[Payment]:

        records = storage_broker.get(Payment, {
            Payment.payment_invoice_id : invoice_id,
                        Payment.payment_status : status,
            
            }, [], [])
        return records[0] if records else None
    
    def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID"""
        records = storage_broker.get(Payment, {Payment.payment_id: payment_id}, [], [])
        return records[0] if records else None
    
    def update_invoice(self, invoice: Invoice) -> Invoice:
        """Update an invoice"""
        from features.insertion import update_record_in_api
        return update_record_in_api(invoice)
    
    def delete_invoice(self, invoice: Invoice) :
        """Delete an invoice"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(invoice)

    def update_payment(self, payment: Payment) -> Payment:
        """Update a payment"""
        from features.insertion import update_record_in_api
        return update_record_in_api(payment)

    def get_by_invoice_id_and_status(
        self,
        invoice_id: int,
        statuses: Tuple[str, ...] = ("completed", "confirmed", "paid"),
    ) -> Optional[Payment]:
        """
        Return the most recent payment for an invoice whose status is in
        `statuses`, or None.

        Used as an idempotency guard by the order/cart payment workflows:
        if a completed payment already exists for this invoice, a retry
        must not create a second one — even if the invoice row itself was
        never flipped to `paid` (e.g. a crash between finance confirm and
        local persist).

        Returns the newest match (ordered by payment_created_at DESC) so
        that, in the unlikely case of multiple completed payments, the
        caller sees the one most recently attached to the invoice.
        """
        if not statuses:
            return None

        try:
            with storage_broker.session_scope() as session:
                return (
                    session.query(Payment)
                    .filter(
                        Payment.payment_invoice_id == invoice_id,
                        Payment.payment_status.in_(list(statuses)),
                    )
                    .order_by(desc(Payment.payment_created_at))
                    .first()
                )
        except Exception as e:
            logger.error(
                "Failed to get payment for invoice %s with statuses %s: %s",
                invoice_id, statuses, e,
            )
            return None

    def has_completed_refund(self, invoice_id: int) -> bool:
        try:
            with storage_broker.session_scope() as session:
                
                return (
                    session.query(Payment)
                    .filter(
                        Payment.payment_invoice_id == invoice_id,
                        Payment.payment_type == "refund",
                        Payment.payment_status == "completed",
                    )
                    .count() > 0
                )
        except Exception as e:
                    logger.error(
                        "Failed to check for completed refund for invoice %s: %s",
                        invoice_id , e,
                    )
                    return None


    def create_refund_payment(
        self, invoice_id: int, amount, reference: Optional[str] = None
    ) -> Payment:
        payment = Payment(
            payment_invoice_id=invoice_id,
            payment_amount=amount,
            payment_method="refund",
            payment_status="completed",
            payment_type="refund",
            payment_reference=reference
                or f"REF-{invoice_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            payment_notes=f"Refund against invoice {invoice_id}",
        )
        with storage_broker.session_scope() as session:
            session.add(payment)
            session.commit()
        return payment