# policies/placed_order_policy.py
"""
PlacedOrderPolicy — PlacedOrder status rules, built on TransitionEngine.

States (from `order_state` enum, stored UPPERCASE):
    PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED, REFUNDED

Transitions (from the state diagram):

    PENDING     → PROCESSING
    PROCESSING  → SHIPPED
    SHIPPED     → DELIVERED
    DELIVERED   → REFUNDED

    PENDING     → CANCELLED
    PROCESSING  → CANCELLED
    SHIPPED     → CANCELLED

Predicates take a `PlacedOrder` instance directly. External signals
(payment paid, delivery confirmed, delivery delivered, refund completed)
come in as keyword arguments on `decide(...)`.

Naming: the policy class is `PlacedOrderPolicy` — matching the ORM class
name, not the file or the colloquial "Order". If you have a service-layer
`OrderPolicy` that wraps this one, it should delegate to this class, not
replace it. One source of truth for the state graph.
"""

from typing import Any

from core.models.models import PlacedOrder

from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
)


# ============================================================================
# PREDICATES
# ============================================================================

def has_items(order: PlacedOrder) -> bool:
    """PENDING → PROCESSING: an order without items can't be processed."""
    items = getattr(order, 'ordered_item', None) or []
    return len(items) > 0


def payment_confirmed(
    order: PlacedOrder, *, payment_paid: bool = False
) -> bool:
    """PENDING → PROCESSING: the invoice must be settled."""
    return payment_paid


def delivery_confirmed(
    order: PlacedOrder, *, delivery_confirmed: bool = False
) -> bool:
    """PROCESSING → SHIPPED: at least one delivery has shipped."""
    return delivery_confirmed


def delivery_delivered(
    order: PlacedOrder, *, delivery_delivered: bool = False
) -> bool:
    """SHIPPED → DELIVERED: every delivery reached the recipient."""
    return delivery_delivered


def cancellable(order: PlacedOrder) -> bool:
    """
    * → CANCELLED: cancellable while the order hasn't been fully
    delivered. Once DELIVERED, the path is REFUNDED, not CANCELLED.
    """
    status = (order.order_state or '').upper()
    return status in {'PENDING', 'PROCESSING', 'SHIPPED'}


def refund_settled(
    order: PlacedOrder, *, refund_completed: bool = False
) -> bool:
    """DELIVERED → REFUNDED: the finance side has issued the refund."""
    return refund_completed


# ============================================================================
# POLICY
# ============================================================================

class PlacedOrderPolicy(PolicyBase):
    """PlacedOrder status rules."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                'PENDING',
                'PROCESSING',
                'SHIPPED',
                'DELIVERED',
                'CANCELLED',
                'REFUNDED',
            },
            initial_state='PENDING',
            terminal_states={'CANCELLED', 'REFUNDED'},
            normalize=lambda s: (s or 'PENDING').upper(),
        )

        registry.add_many([
            # ── PENDING ─────────────────────────────────────────────
            Transition(
                source='PENDING',
                target='PROCESSING',
                predicate=payment_confirmed,
                side_effects=(
                    'assign_delivery',
                    'dispatch_inventory_confirmation',
                ),
                name='pending_to_processing',
            ),
            Transition(
                source='PENDING',
                target='CANCELLED',
                predicate=cancellable,
                side_effects=(
                    'release_inventory',
                    'cancel_invoice',
                    'cancel_deliveries',
                ),
                name='pending_to_cancelled',
            ),

            # ── PROCESSING ──────────────────────────────────────────
            Transition(
                source='PROCESSING',
                target='SHIPPED',
                predicate=delivery_confirmed,
                side_effects=('broadcast_shipped',),
                name='processing_to_shipped',
            ),
            Transition(
                source='PROCESSING',
                target='CANCELLED',
                predicate=cancellable,
                side_effects=(
                    'release_inventory',
                    'cancel_invoice',
                    'cancel_deliveries',
                ),
                name='processing_to_cancelled',
            ),

            # ── SHIPPED ─────────────────────────────────────────────
            Transition(
                source='SHIPPED',
                target='DELIVERED',
                predicate=delivery_delivered,
                side_effects=(
                    'confirm_inventory',
                    'close_invoice',
                ),
                name='shipped_to_delivered',
            ),
            Transition(
                source='SHIPPED',
                target='CANCELLED',
                predicate=cancellable,
                side_effects=(
                    'release_inventory',
                    'cancel_invoice',
                    'cancel_deliveries',
                    'refund_if_paid',
                ),
                name='shipped_to_cancelled',
            ),

            # ── DELIVERED ───────────────────────────────────────────
            Transition(
                source='DELIVERED',
                target='REFUNDED',
                predicate=refund_settled,
                side_effects=(
                    'refund_payment',
                    'return_inventory',
                ),
                name='delivered_to_refunded',
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_order(
        self,
        order: PlacedOrder,
        target: str,
        **extras: Any,
    ) -> Decision:
        """Decide using the order's own state as the current state."""
        current = order.order_state or self.initial_state
        return self.decide(current, target, order, **extras)

    def is_final(self, state: str) -> bool:
        """No forward progress possible — order is done either way."""
        return self.normalize(state) in {'DELIVERED', 'CANCELLED', 'REFUNDED'}

    def is_cancellable(self, order: PlacedOrder) -> bool:
        return cancellable(order)

    def is_settled(self, order: PlacedOrder) -> bool:
        """Delivered, cancelled, or refunded — no further action needed."""
        return self.is_final(order.order_state or '')

    def is_active(self, order: PlacedOrder) -> bool:
        """Anything before SHIPPED is actively being worked on."""
        return self.normalize(
            order.order_state or ''
        ) in {'PENDING', 'PROCESSING'}

    # ── Error mapping ────────────────────────────────────────────────

    def transition_error(self, decision: Decision) -> Exception:
        from core.exceptions.specific.order_exceptions import (
            InvalidOrderStatusException,
            OrderStatusTransitionException,
        )
        if not self.is_valid(decision.target):
            return InvalidOrderStatusException(
                status=decision.target,
                valid_statuses=sorted(self.valid_states),
            )
        return OrderStatusTransitionException(
            current_status=decision.current,
            new_status=decision.target,
            allowed_transitions=sorted(
                self.allowed_targets(decision.current)
            ),
        )

    def invalid_state_error(self, state: str) -> Exception:
        from core.exceptions.specific.order_exceptions import (
            InvalidOrderStatusException,
        )
        return InvalidOrderStatusException(
            status=state,
            valid_statuses=sorted(self.valid_states),
        )