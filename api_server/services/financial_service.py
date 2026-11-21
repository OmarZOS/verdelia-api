# services/financial_service.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from repositories.financial_repository import FinancialRepository
from core.models.api_models import InvoiceStatus, Payment_API, Deposit_API, AdditionalFee_API
from core.exceptions.specific.finance_exceptions import (
    PaymentNotFoundException,
    PaymentCreationFailedException,
)
from core.exceptions.handler import APIException
from core.messages import *
from core.models.models import Payment, AdditionalFee


# Payment statuses that count as money actually received.
# Note: 'partial' contributes only its own amount; the total is computed
# per-payment in _recompute_invoice_status().
SETTLED_PAYMENT_STATUSES = {"completed", "partial"}

# Allowed payment status transitions, matching the real DB enum:
#   pending | processing | completed | partial | failed | cancelled
PAYMENT_TRANSITIONS: Dict[str, set] = {
    "pending":    {"processing", "completed", "failed", "cancelled"},
    "processing": {"completed", "failed", "cancelled"},
    "completed":  {"cancelled"},   # refund/void path
    "partial":    {"completed", "cancelled"},
    "failed":     {"pending"},     # retry
    "cancelled":  set(),           # terminal
}


class FinancialService:
    """Service for financial operations."""

    def __init__(self):
        self.financial_repo = FinancialRepository()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _norm_status(status: Optional[str]) -> str:
        """Normalize a status string to lowercase for comparison."""
        return (status or "").strip().lower()

    def _recompute_invoice_status(self, invoice) -> None:
        """
        Recompute an invoice's status from the set of its settled payments.

        Rules:
          - No settled payments                 → unpaid
          - Sum of settled < invoice total      → partially_paid
          - Sum of settled >= invoice total     → paid
        """
        settled_total = 0.0
        for p in (invoice.payment or []):
            if self._norm_status(getattr(p, "payment_status", None)) in SETTLED_PAYMENT_STATUSES:
                settled_total += float(getattr(p, "payment_amount", 0) or 0)

        total_due = float(invoice.grand_total or 0)

        if settled_total <= 0:
            new_status = InvoiceStatus.UNPAID
        elif settled_total >= total_due:
            new_status = InvoiceStatus.PAID
        else:
            new_status = InvoiceStatus.PARTIALLY_PAID

        if self._norm_status(invoice.invoice_status) != self._norm_status(new_status):
            invoice.invoice_status = new_status
            self.financial_repo.update_invoice(invoice)

    # ------------------------------------------------------------------ #
    # Payment creation
    # ------------------------------------------------------------------ #

    def create_payment(self, payment_data: Payment_API) -> Payment:
        """
        Create a payment and (re)compute the linked invoice's status.

        Default status is 'pending' when the client doesn't specify one.
        """
        payment_status = self._norm_status(payment_data.payment_status) or "pending"

        payment = Payment(
            payment_amount=payment_data.payment_amount,
            payment_method=payment_data.payment_method,
            payment_status=payment_status,
            payment_reference=payment_data.payment_reference,
            payment_notes=payment_data.payment_notes,
        )
        if payment_data.payment_invoice_id:
            payment.payment_invoice_id = payment_data.payment_invoice_id

        created = self.financial_repo.create_payment(payment)

        if payment_data.payment_invoice_id:
            invoice = self.financial_repo.get_invoice_by_id(payment_data.payment_invoice_id)
            if invoice:
                self._recompute_invoice_status(invoice)

        return created

    # ------------------------------------------------------------------ #
    # Payment status transitions
    # ------------------------------------------------------------------ #

    def update_payment_status(self, payment_id, new_status, note=None):
        payment = self.financial_repo.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundException(payment_id=payment_id)

        current = self._norm_status(payment.payment_status)
        target = self._norm_status(new_status)
        allowed = PAYMENT_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise PaymentCreationFailedException(
                error=(
                    f"Invalid payment status transition: "
                    f"'{current}' → '{target}'"
                ),
                details={
                    "payment_id": payment_id,
                    "current_status": current,
                    "requested_status": target,
                    "allowed": sorted(allowed),
                },
            )
        return self.apply_payment_status(payment, target, reason=note)

    def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        return self.financial_repo.get_payment_by_id(payment_id)

    # ------------------------------------------------------------------ #
    # Additional fees
    # ------------------------------------------------------------------ #

    def create_fee(self, fee_data: AdditionalFee_API) -> AdditionalFee:
        fee = AdditionalFee(
            fee_name=fee_data.fee_name,
            fee_amount=fee_data.fee_amount,
            fee_type=fee_data.fee_type,
            fee_description=fee_data.fee_description,
        )
        return self.financial_repo.create_fee(fee)

    # ------------------------------------------------------------------ #
    # Generic / legacy
    # ------------------------------------------------------------------ #

    def create_financial_item(
        self,
        payment: Optional[Payment_API] = None,
        deposit: Optional[Deposit_API] = None,
        fee: Optional[AdditionalFee_API] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if payment:
            result["payment"] = self.create_payment(payment)
        if deposit:
            result["deposit"] = self.create_deposit(deposit)
        if fee:
            result["fee"] = self.create_fee(fee)
        return result

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #

    def get_payments(
        self,
        invoice_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Payment]:
        return self.financial_repo.get_payments(invoice_id, offset, limit) or []

    def get_deposits(
        self,
        cart_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Any]:
        return self.financial_repo.get_deposits(cart_id, offset, limit) or []

    def get_financial_items(
            self,
            supplier_id: int = 0,
            person_id: int = 0,
            client_id: int = 0,
            seller_id: int = 0,
            cart_id: int = 0,
            order_id: int = 0,
            deposit_id: int = 0,
            invoice_id: int = 0,
            offset: int = 0,
            limit: int = 10,
        ) -> Dict[str, Any]:
            return {
                "payments": self.get_payments(invoice_id or None, offset, limit),
                "deposits": self.get_deposits(cart_id or None, offset, limit),
                "invoices": [],
                "receipts": [],
            }
    def apply_payment_status(
        self,
        payment: Payment,
        new_status: str,
        *,
        reason: Optional[str] = None,
    ) -> Payment:
        """
        Persist a status the caller has already validated through
        PaymentPolicy. Does NOT re-check transitions — the policy owns
        that. Recomputes the invoice status.
        """
        previous = self._norm_status(payment.payment_status)
        target = self._norm_status(new_status)

        payment.payment_status = target
        if reason:
            stamped = f"[{datetime.utcnow().isoformat()}] {target}: {reason}"
            payment.payment_notes = (
                f"{payment.payment_notes}\n{stamped}".strip()
                if payment.payment_notes else stamped
            )

        updated = self.financial_repo.update_payment(payment)

        if updated.payment_invoice_id:
            invoice = self.financial_repo.get_invoice_by_id(
                updated.payment_invoice_id
            )
            if invoice:
                if target == "cancelled" and previous in (
                    "completed", "partial"
                ):
                    invoice.invoice_status = InvoiceStatus.REFUNDED
                    self.financial_repo.update_invoice(invoice)
                else:
                    self._recompute_invoice_status(invoice)

        return updated