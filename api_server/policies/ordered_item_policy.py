# policies/ordered_item_policy.py
"""
OrderedItemPolicy — OrderedItem status rules, built on TransitionEngine.

States (from `delivery_status` enum):
    pending, processing, shipped, delivered, cancelled, returned, partial

Transitions (from the state diagram):

    pending     → processing
    processing  → shipped
    shipped     → delivered
    delivered   → returned

    pending     → cancelled
    processing  → cancelled
    shipped     → cancelled

    pending     → partial
    processing  → partial
    partial     → delivered
    partial     → cancelled

Predicates take an `OrderedItem` instance directly. Any external signal
(inventory reserved, delivery confirmed, return received, etc.) is a
keyword argument on `decide(...)`.

The item carries an `ordered_quantity` and a `reserved_quantity` — the
`partial` state is meaningful when a subset of the ordered quantity is
shipped. Predicates that care about quantities read them off the instance.
"""

from typing import Any

from core.models.models import OrderedItem

from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
)


# ============================================================================
# PREDICATES
# ============================================================================

def inventory_reserved(item: OrderedItem) -> bool:
    """
    pending → processing: processing starts once a reservation exists.
    Falls back to True when the column is unset so callers without a
    reservation step aren't blocked.
    """
    reserved = item.reserved_quantity or 0
    return reserved > 0 or item.ordered_quantity == 0


def has_positive_quantity(item: OrderedItem) -> bool:
    """Any transition to `processing` or `shipped` needs a real quantity."""
    return (item.ordered_quantity or 0) > 0


def delivery_confirmed(
    item: OrderedItem, *, delivery_confirmed: bool = True
) -> bool:
    """processing → shipped: the parent delivery has shipped this item."""
    return delivery_confirmed


def delivery_delivered(
    item: OrderedItem, *, delivery_delivered: bool = True
) -> bool:
    """shipped/partial → delivered: goods arrived."""
    return delivery_delivered


def split_confirmed(
    item: OrderedItem, *, split_confirmed: bool = True
) -> bool:
    """
    pending/processing → partial: the item is split across shipments.

    Optional quantity guard: if the caller supplies a `split_quantity`,
    it must be strictly less than `ordered_quantity` (otherwise the
    split isn't partial).
    """
    if not split_confirmed:
        return False
    split_quantity = getattr(item, '_split_quantity', None)
    if split_quantity is None:
        return True
    return 0 < split_quantity < (item.ordered_quantity or 0)


def cancellable(item: OrderedItem) -> bool:
    """
    * → cancelled: only before the item is in physical motion.
    Once `shipped`, cancel via `returned`, not `cancelled`.
    """
    status = (item.delivery_status or '').lower()
    return status in {'pending', 'processing'}


def return_received(
    item: OrderedItem, *, return_received: bool = True
) -> bool:
    """delivered → returned: goods came back."""
    return return_received


# ============================================================================
# POLICY
# ============================================================================

class OrderedItemPolicy(PolicyBase):
    """OrderedItem status rules."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                'pending',
                'processing',
                'shipped',
                'delivered',
                'cancelled',
                'returned',
                'partial',
            },
            initial_state='pending',
            terminal_states={'cancelled', 'returned'},
            normalize=lambda s: (s or 'pending').lower(),
        )

        registry.add_many([
            # ── pending ─────────────────────────────────────────────
            Transition(
                source='pending',
                target='processing',
                predicate=inventory_reserved,
                side_effects=('assign_picker',),
                name='pending_to_processing',
            ),
            Transition(
                source='pending',
                target='cancelled',
                predicate=cancellable,
                side_effects=('release_item_inventory',),
                name='pending_to_cancelled',
            ),
            Transition(
                source='pending',
                target='partial',
                predicate=split_confirmed,
                side_effects=('split_item',),
                name='pending_to_partial',
            ),

            # ── processing ──────────────────────────────────────────
            Transition(
                source='processing',
                target='shipped',
                predicate=delivery_confirmed,
                side_effects=('hand_off_to_delivery',),
                name='processing_to_shipped',
            ),
            Transition(
                source='processing',
                target='cancelled',
                predicate=cancellable,
                side_effects=('release_item_inventory',),
                name='processing_to_cancelled',
            ),
            Transition(
                source='processing',
                target='partial',
                predicate=split_confirmed,
                side_effects=('split_item',),
                name='processing_to_partial',
            ),

            # ── shipped ─────────────────────────────────────────────
            Transition(
                source='shipped',
                target='delivered',
                predicate=delivery_delivered,
                side_effects=('confirm_item_inventory',),
                name='shipped_to_delivered',
            ),
            Transition(
                source='shipped',
                target='cancelled',
                predicate=cancellable,
                side_effects=('release_item_inventory',),
                name='shipped_to_cancelled',
            ),

            # ── partial ─────────────────────────────────────────────
            Transition(
                source='partial',
                target='delivered',
                predicate=delivery_delivered,
                side_effects=('confirm_remaining_inventory',),
                name='partial_to_delivered',
            ),
            Transition(
                source='partial',
                target='cancelled',
                predicate=cancellable,
                side_effects=('release_remaining_inventory',),
                name='partial_to_cancelled',
            ),

            # ── delivered ───────────────────────────────────────────
            Transition(
                source='delivered',
                target='returned',
                predicate=return_received,
                side_effects=('restock_item', 'refund_item_if_paid'),
                name='delivered_to_returned',
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_item(
        self,
        item: OrderedItem,
        target: str,
        **extras: Any,
    ) -> Decision:
        """Decide using the item's own status as the current state."""
        current = item.delivery_status or self.initial_state
        return self.decide(current, target, item, **extras)

    def is_final(self, state: str) -> bool:
        return self.normalize(state) in {
            'delivered', 'cancelled', 'returned',
        }

    def is_in_flight(self, state: str) -> bool:
        return self.normalize(state) == 'shipped'

    def is_cancellable(self, item: OrderedItem) -> bool:
        return cancellable(item)

    def is_partial(self, item: OrderedItem) -> bool:
        """
        True when the item is mid-split: some quantity delivered, some
        remaining. Reads the reserved/ordered quantities rather than the
        status, so callers can inspect without inferring from labels.
        """
        ordered = item.ordered_quantity or 0
        reserved = item.reserved_quantity or 0
        return 0 < reserved < ordered

    def remaining_quantity(self, item: OrderedItem) -> int:
        """How many units are still outstanding on this item."""
        ordered = item.ordered_quantity or 0
        reserved = item.reserved_quantity or 0
        return max(0, ordered - reserved)

    # ── Error mapping ────────────────────────────────────────────────

    def transition_error(self, decision: Decision) -> Exception:
        return ValueError(
            f"Illegal ordered-item transition '{decision.current}' → "
            f"'{decision.target}': {decision.reason}"
        )

    def invalid_state_error(self, state: str) -> Exception:
        return ValueError(
            f"Invalid ordered-item status '{state}'. "
            f"Valid: {sorted(self.valid_states)}"
        )