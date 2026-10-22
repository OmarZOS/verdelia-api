# policies/invoice_policy.py
"""
InvoicePolicy — Invoice status rules, built on TransitionEngine.

States (from `invoice_status` enum, stored lowercase):
    unpaid, paid, canceled, partially_paid, overdue, refunded

Transitions (from the state diagram):

    unpaid          → partially_paid
    unpaid          → paid
    unpaid          → overdue
    unpaid          → canceled

    partially_paid  → paid
    partially_paid  → overdue
    partially_paid  → canceled

    overdue         → paid
    overdue         → canceled

    paid            → refunded

Predicates take an `Invoice` instance directly. External signals (amount
received, refund completed, write-off authorised) come in as keyword
arguments on `decide(...)`.

The invoice carries `grand_total`, `invoice_due_date`, and
`invoice_status`. Predicates that reason about partial vs. full payment
receive the captured amount as a keyword argument — the invoice itself
has no "paid so far" column, so the caller (usually after summing its
payments) supplies it.
"""

from typing import Any, Optional
from datetime import date, datetime

from core.models.models import Invoice

from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
)


# ============================================================================
# PREDICATES
# ============================================================================

def has_amount(invoice: Invoice) -> bool:
    """Any invoice that can transition must have a positive total."""
    return float(invoice.grand_total or 0) > 0


def partial_payment_received(
    invoice: Invoice, *, captured_amount: float = 0.0
) -> bool:
    """
    unpaid → partially_paid: some money came in, less than the total.
    """
    total = float(invoice.grand_total or 0)
    captured = float(captured_amount or 0)
    return 0 < captured < total


def full_payment_received(
    invoice: Invoice, *, captured_amount: Optional[float] = None
) -> bool:
    """
    * → paid: the captured amount covers the invoice total.

    When `captured_amount` is omitted, the caller is asserting that the
    invoice is fully paid without quantifying it — accept the transition.
    That's the common case from `process_payment`, which confirms the
    payment and knows the invoice settled.
    """
    total = float(invoice.grand_total or 0)
    if total <= 0:
        return False

    if captured_amount is None:
        return True

    return float(captured_amount) >= total


def is_overdue(
    invoice: Invoice, *, now: Optional[date] = None
) -> bool:
    """
    unpaid/partially_paid → overdue: the due date has passed.
    """
    due = invoice.invoice_due_date
    if due is None:
        return False
    reference = now or date.today()
    return due < reference


def no_payment_received(
    invoice: Invoice, *, captured_amount: float = 0.0
) -> bool:
    """
    unpaid → canceled: only when nothing has been captured. An invoice
    with a partial payment cannot be cancelled directly — it must be
    refunded first, or resolved through `partially_paid → canceled`.
    """
    return float(captured_amount or 0) <= 0


def partial_refund_completed(
    invoice: Invoice, *, refund_completed: bool = False
) -> bool:
    """
    partially_paid → canceled: the partial amount already captured has
    been refunded back.
    """
    return refund_completed


def write_off_authorised(
    invoice: Invoice, *, write_off_authorised: bool = False
) -> bool:
    """
    overdue → canceled: someone with authority decided to write off the
    invoice rather than pursue collection.
    """
    return write_off_authorised


def refund_completed(
    invoice: Invoice, *, refund_completed: bool = False
) -> bool:
    """paid → refunded: the refund has been issued back to the payer."""
    return refund_completed


# ============================================================================
# POLICY
# ============================================================================

class InvoicePolicy(PolicyBase):
    """Invoice status rules."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                'unpaid',
                'partially_paid',
                'paid',
                'overdue',
                'canceled',
                'refunded',
            },
            initial_state='unpaid',
            terminal_states={'canceled', 'refunded'},
            normalize=lambda s: (s or 'unpaid').lower(),
        )

        registry.add_many([
            # ── unpaid ──────────────────────────────────────────────
            Transition(
                source='unpaid',
                target='partially_paid',
                predicate=partial_payment_received,
                side_effects=('record_partial_payment',),
                name='unpaid_to_partially_paid',
            ),
            Transition(
                source='unpaid',
                target='paid',
                predicate=full_payment_received,
                side_effects=(
                    'order_advance',
                    'delivery_may_start',
                    'close_invoice',
                ),
                name='unpaid_to_paid',
            ),
            Transition(
                source='unpaid',
                target='overdue',
                predicate=is_overdue,
                side_effects=(
                    'notify_payer',
                    'apply_late_fee_policy',
                ),
                name='unpaid_to_overdue',
            ),
            Transition(
                source='unpaid',
                target='canceled',
                predicate=no_payment_received,
                side_effects=('release_inventory',),
                name='unpaid_to_canceled',
            ),

            # ── partially_paid ──────────────────────────────────────
            Transition(
                source='partially_paid',
                target='paid',
                predicate=full_payment_received,
                side_effects=(
                    'order_advance',
                    'delivery_may_start',
                    'close_invoice',
                ),
                name='partially_paid_to_paid',
            ),
            Transition(
                source='partially_paid',
                target='overdue',
                predicate=is_overdue,
                side_effects=(
                    'notify_payer',
                    'apply_late_fee_policy',
                ),
                name='partially_paid_to_overdue',
            ),
            Transition(
                source='partially_paid',
                target='canceled',
                predicate=partial_refund_completed,
                side_effects=('refund_partial_payment',),
                name='partially_paid_to_canceled',
            ),

            # ── overdue ─────────────────────────────────────────────
            Transition(
                source='overdue',
                target='paid',
                predicate=full_payment_received,
                side_effects=('order_advance', 'close_invoice'),
                name='overdue_to_paid',
            ),
            Transition(
                source='overdue',
                target='canceled',
                predicate=write_off_authorised,
                side_effects=('write_off',),
                name='overdue_to_canceled',
            ),

            # ── paid ────────────────────────────────────────────────
            Transition(
                source='paid',
                target='refunded',
                predicate=refund_completed,
                side_effects=(
                    'refund_payment',
                    'order_refund',
                    'delivery_refund',
                ),
                name='paid_to_refunded',
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_invoice(
        self,
        invoice: Invoice,
        target: str,
        **extras: Any,
    ) -> Decision:
        """Decide using the invoice's own status as the current state."""
        current = invoice.invoice_status or self.initial_state
        return self.decide(current, target, invoice, **extras)

    def is_final(self, state: str) -> bool:
        """Canceled or refunded — no further money movement expected."""
        return self.normalize(state) in {'canceled', 'refunded'}

    def is_settled(self, state: str) -> bool:
        """
        Money has landed and stays landed: `paid`. `refunded` is settled
        the other way. `canceled` never collected anything.
        """
        return self.normalize(state) in {'paid', 'refunded', 'canceled'}

    def is_collectible(self, state: str) -> bool:
        """Money is still owed on this invoice."""
        return self.normalize(state) in {
            'unpaid', 'partially_paid', 'overdue',
        }

    def is_refundable(self, state: str) -> bool:
        """Only paid invoices can be refunded."""
        return self.normalize(state) == 'paid'

    def needs_attention(self, invoice: Invoice) -> bool:
        """Overdue, or due today with a balance outstanding."""
        if not self.is_collectible(invoice.invoice_status or ''):
            return False

        due = invoice.invoice_due_date
        if due is None:
            return False

        return due <= date.today()

    # ── Error mapping ────────────────────────────────────────────────

    def transition_error(self, decision: Decision) -> Exception:
        return ValueError(
            f"Illegal invoice transition '{decision.current}' → "
            f"'{decision.target}': {decision.reason}"
        )

    def invalid_state_error(self, state: str) -> Exception:
        return ValueError(
            f"Invalid invoice status '{state}'. "
            f"Valid: {sorted(self.valid_states)}"
        )