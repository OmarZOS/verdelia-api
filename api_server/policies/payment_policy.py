# policies/payment_policy.py
"""
PaymentPolicy — Payment status rules, built on TransitionEngine.

Every predicate takes a `Payment` instance. No `Mapping`, no `ctx`, no
`getattr`. If a rule needs a second value (an expected amount), it's a
keyword argument the caller supplies.
"""

from typing import Any


from core.models.models import Payment
from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
)


# ============================================================================
# PREDICATES — every one takes the Payment directly
# ============================================================================

def gateway_charge_started(payment: Payment) -> bool:
    """pending → processing: the gateway charge must be in flight."""
    return bool(payment.payment_amount)


def gateway_failed(payment: Payment) -> bool:
    """pending/processing/partial → failed: gateway returned a failure."""
    if not payment.payment_amount:
        return False
    return float(payment.payment_amount or 0) <= 0


def full_amount_captured(
    payment: Payment, *, expected_amount: float = 0.0
) -> bool:
    """processing/partial → completed: the full amount was captured."""
    captured = float(payment.payment_amount or 0)
    if expected_amount > 0:
        return captured >= expected_amount
    return captured > 0


def partial_amount_captured(
    payment: Payment, *, expected_amount: float = 0.0
) -> bool:
    """processing → partial: some, but not all, of the amount was captured."""
    captured = float(payment.payment_amount or 0)
    if captured <= 0:
        return False
    if expected_amount > 0:
        return captured < expected_amount
    return True


def cancellable(payment: Payment) -> bool:
    """* → cancelled: no completed settlement has occurred."""
    status = (payment.payment_status or '').lower()
    return status not in {'completed', 'cancelled'}


# ============================================================================
# POLICY
# ============================================================================

class PaymentPolicy(PolicyBase):
    """Payment status rules."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                'pending', 'processing', 'completed',
                'partial', 'failed', 'cancelled',
            },
            initial_state='pending',
            terminal_states={'completed', 'cancelled'},
            normalize=lambda s: (s or 'pending').lower(),
        )

        registry.add_many([
            Transition(
                source='pending', target='processing',
                predicate=gateway_charge_started,
                side_effects=('gateway_charge_started',),
                name='pending_to_processing',
            ),
            Transition(
                source='pending', target='failed',
                predicate=gateway_failed,
                side_effects=('notify_user',),
                name='pending_to_failed',
            ),
            Transition(
                source='pending', target='cancelled',
                predicate=cancellable,
                side_effects=('release_gateway_hold',),
                name='pending_to_cancelled',
            ),

            Transition(
                source='processing', target='completed',
                predicate=full_amount_captured,
                side_effects=('invoice_mark_paid', 'order_advance'),
                name='processing_to_completed',
            ),
            Transition(
                source='processing', target='partial',
                predicate=partial_amount_captured,
                side_effects=('invoice_mark_partially_paid',),
                name='processing_to_partial',
            ),
            Transition(
                source='processing', target='failed',
                predicate=gateway_failed,
                side_effects=('notify_user',),
                name='processing_to_failed',
            ),
            Transition(
                source='processing', target='cancelled',
                predicate=cancellable,
                side_effects=('release_gateway_hold',),
                name='processing_to_cancelled',
            ),

            Transition(
                source='partial', target='completed',
                predicate=full_amount_captured,
                side_effects=('invoice_mark_paid', 'order_advance'),
                name='partial_to_completed',
            ),
            Transition(
                source='partial', target='failed',
                predicate=gateway_failed,
                side_effects=('notify_user',),
                name='partial_to_failed',
            ),
            Transition(
                source='partial', target='cancelled',
                predicate=cancellable,
                side_effects=('release_gateway_hold',),
                name='partial_to_cancelled',
            ),

            Transition(
                source='failed', target='cancelled',
                predicate=lambda payment: True,
                side_effects=(),
                name='failed_to_cancelled',
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_payment(
        self,
        payment: Payment,
        target: str,
        **extras: Any,
    ) -> Decision:
        """Decide using the payment's own status as the current state."""
        current = payment.payment_status or self.initial_state
        return self.decide(current, target, payment, **extras)

    def is_settled(self, state: str) -> bool:
        return self.normalize(state) in {'completed', 'cancelled'}

    def is_refundable(self, state: str) -> bool:
        return self.normalize(state) == 'completed'

    # ── Error mapping ────────────────────────────────────────────────

    def transition_error(self, decision: Decision) -> Exception:
        return ValueError(
            f"Illegal payment transition '{decision.current}' → "
            f"'{decision.target}': {decision.reason}"
        )

    def invalid_state_error(self, state: str) -> Exception:
        return ValueError(
            f"Invalid payment status '{state}'. "
            f"Valid: {sorted(self.valid_states)}"
        )