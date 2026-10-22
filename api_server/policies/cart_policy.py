# policies/cart_policy.py
"""
CartPolicy — Cart status rules, built on TransitionEngine.

States (from `cart_status` enum, stored lowercase):
    open, pending, completed, canceled, partial, checkout, abandoned

Transitions (from the state diagram):

    open       → pending
    open       → abandoned
    open       → canceled

    pending    → checkout
    pending    → partial
    pending    → canceled

    checkout   → completed
    checkout   → partial

    partial    → completed
    partial    → canceled

    abandoned  → open

Predicates take a `Cart` instance as their first positional
argument (the `input` the engine hands them) and any caller
signals as keyword arguments. Predicates are declared with
`**_` so the engine can pass the full set of caller extras
without every predicate having to know the union.

Note on `checkout`: it is a *transient* state — the invoice
has been issued and the delivery has been created, but the
money and the goods haven't moved yet. From `checkout` the cart
either resolves to `completed` (paid and fulfilled) or falls
back to `partial` (only some of the contents were fulfilled).
It cannot go straight to `canceled`: once an invoice exists,
cancellation must go through the invoice. See `cancellable`.
"""

from typing import Any, Iterable, Optional

from repositories.cart_repository import CartRepository
from core.models.models import Cart

from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
)


# ============================================================================
# SMALL HELPERS
# ============================================================================

def _iter_or_empty(value: Optional[Iterable[Any]]) -> Iterable[Any]:
    """
    Coerce a possibly-None relationship/repo return into an iterable.

    SQLAlchemy relationships and repo methods frequently return None
    instead of [] for empty sets. Iterating over None raises, so every
    loop in this module goes through this helper.
    """
    return value or ()


def _status(cart: Cart) -> str:
    """Lower-cased cart status, defaulting to 'open'."""
    return (cart.cart_status or "open").lower()


def _item_status(item: Any) -> str:
    """Lower-cased ordered-item delivery status, defaulting to ''."""
    return (getattr(item, "ordered_item_delivery_status", "") or "").lower()


def _service_status(svc: Any) -> str:
    """Lower-cased ordered-service delivery status, defaulting to ''."""
    return (
        getattr(svc, "ordered_service_delivery_status", "") or ""
    ).lower()


# Statuses that mean "this line has actually been delivered / done".
_DELIVERED_LINE_STATUSES = frozenset({"delivered", "completed"})

# Statuses that mean "this line was cancelled and does not owe anything".
_DEAD_LINE_STATUSES = frozenset({"cancelled", "canceled", "returned", "no_show"})


# ============================================================================
# PREDICATES
# ============================================================================

def has_items(cart: Cart, **_: Any) -> bool:
    """
    open → pending: a cart with no line items (items or services)
    cannot move to pending. Reads both relationships so a
    services-only cart still qualifies.
    """
    items = list(_iter_or_empty(getattr(cart, "ordered_item", None)))
    services = list(_iter_or_empty(getattr(cart, "ordered_service", None)))
    return (len(items) + len(services)) > 0


def has_provider(cart: Cart, **_: Any) -> bool:
    """open → pending: a cart must be scoped to a provider."""
    return bool(cart.provider_id)


def cart_stale(
    cart: Cart, *, stale: bool = False, **_: Any
) -> bool:
    """
    open/pending → abandoned: only stale carts are auto-abandoned.

    `stale` is asserted by the caller (typically a periodic sweeper
    that compares `updated_at` against a threshold). Defaults to
    False so a naive `decide(...)` never abandons a live cart.
    """
    return bool(stale)


def checkout_ready(
    cart: Cart,
    *,
    invoice_issued: bool = False,
    delivery_created: bool = False,
    **_: Any,
) -> bool:
    """
    pending → checkout: the cart is paid-and-billed but not yet
    fulfilled. Two things must be true:

      * the cart row carries an invoice id (invoice has been issued),
      * the caller asserts a delivery exists for it.

    Structural check first (no `None > 0` on the FK), then the
    caller signals.
    """
    if not (cart.invoice_id or 0) > 0:
        return False
    return bool(invoice_issued and delivery_created)


def partial_fulfilment(
    cart: Cart,
    *,
    cart_repo: Optional[CartRepository] = None,
    **_: Any,
) -> bool:
    """
    pending/checkout → partial: at least one line has been delivered
    while at least one has not.

    NOTE ON SEMANTICS: the previous version of this predicate treated
    `product_reserved_quantity == 0` on a consumption as evidence of
    fulfilment. That conflates stock *reservation* with delivery
    status. A zero reservation is the state of a consumption that has
    not been reserved yet (or was already released), not evidence
    that the line was delivered. The current predicate only trusts
    delivery statuses on the cart's lines.
    """
    repo = cart_repo or CartRepository()

    delivered = 0
    pending = 0

    for item in _iter_or_empty(repo.get_ordered_items_for_cart(cart.cart_id)):
        status = _item_status(item)
        if status in _DELIVERED_LINE_STATUSES:
            delivered += 1
        elif status not in _DEAD_LINE_STATUSES:
            pending += 1

    for svc in _iter_or_empty(
        repo.get_ordered_services_for_cart(cart.cart_id)
    ):
        status = _service_status(svc)
        if status in _DELIVERED_LINE_STATUSES:
            delivered += 1
        elif status not in _DEAD_LINE_STATUSES:
            pending += 1

    return delivered > 0 and pending > 0


def fully_fulfilled(
    cart: Cart,
    *,
    cart_repo: Optional[CartRepository] = None,
    **_: Any,
) -> bool:
    """
    checkout/partial → completed: every line item has been delivered
    (or the remaining items explicitly cancelled with the invoice
    settled).

    A cart with no lines at all is NOT considered fulfilled. It's an
    empty cart, which should have been cancelled or reopened, not
    completed. This guards against the "zero lines, zero pending,
    therefore done" failure mode.
    """
    repo = cart_repo or CartRepository()

    items = list(
        _iter_or_empty(repo.get_ordered_items_for_cart(cart.cart_id))
    )
    services = list(
        _iter_or_empty(repo.get_ordered_services_for_cart(cart.cart_id))
    )

    if not items and not services:
        return False

    for item in items:
        if _item_status(item) not in _DELIVERED_LINE_STATUSES:
            return False

    for svc in services:
        if _service_status(svc) not in _DELIVERED_LINE_STATUSES:
            return False

    return True


def cancellable(cart: Cart, **_: Any) -> bool:
    """
    * → canceled: only before checkout. Once an invoice exists
    (status == 'checkout'), cancellation flows through the invoice,
    not the cart.
    """
    return _status(cart) in {"open", "pending", "partial"}


# ============================================================================
# POLICY
# ============================================================================

class CartPolicy(PolicyBase):
    """Cart status rules."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                "open",
                "pending",
                "checkout",
                "completed",
                "partial",
                "canceled",
                "abandoned",
            },
            initial_state="open",
            terminal_states={"completed", "canceled"},
            normalize=lambda s: (s or "open").lower(),
        )

        registry.add_many([
            # ── open ────────────────────────────────────────────────
            Transition(
                source="open",
                target="pending",
                predicate=lambda cart, **_: (
                    has_items(cart) and has_provider(cart)
                ),
                side_effects=("lock_prices",),
                name="open_to_pending",
            ),
            Transition(
                source="open",
                target="abandoned",
                predicate=cart_stale,
                side_effects=("archive_cart",),
                name="open_to_abandoned",
            ),
            Transition(
                source="open",
                target="canceled",
                predicate=cancellable,
                side_effects=("release_slot",),
                name="open_to_canceled",
            ),

            # ── pending ─────────────────────────────────────────────
            Transition(
                source="pending",
                target="abandoned",
                predicate=cart_stale,
                side_effects=("archive_cart",),
                name="pending_to_abandoned",
            ),
            Transition(
                source="pending",
                target="checkout",
                predicate=checkout_ready,
                side_effects=("invoice_issued", "delivery_created"),
                name="pending_to_checkout",
            ),
            Transition(
                source="pending",
                target="partial",
                predicate=partial_fulfilment,
                side_effects=("split_fulfilment",),
                name="pending_to_partial",
            ),
            Transition(
                source="pending",
                target="canceled",
                predicate=cancellable,
                side_effects=(
                    "cancel_invoice_if_any",
                    "release_inventory",
                ),
                name="pending_to_canceled",
            ),

            # ── checkout ────────────────────────────────────────────
            Transition(
                source="checkout",
                target="completed",
                predicate=fully_fulfilled,
                side_effects=(
                    "close_invoice",
                    "confirm_inventory",
                ),
                name="checkout_to_completed",
            ),
            Transition(
                source="checkout",
                target="partial",
                predicate=partial_fulfilment,
                side_effects=("split_fulfilment",),
                name="checkout_to_partial",
            ),

            # ── partial ─────────────────────────────────────────────
            Transition(
                source="partial",
                target="completed",
                predicate=fully_fulfilled,
                side_effects=(
                    "close_invoice",
                    "confirm_remaining_inventory",
                ),
                name="partial_to_completed",
            ),
            Transition(
                source="partial",
                target="canceled",
                predicate=cancellable,
                side_effects=(
                    "cancel_remaining_invoice",
                    "release_remaining_inventory",
                    "refund_completed_portion",
                ),
                name="partial_to_canceled",
            ),

            # ── abandoned ───────────────────────────────────────────
            Transition(
                source="abandoned",
                target="open",
                predicate=lambda cart, **_: True,
                side_effects=("reopen_cart",),
                name="abandoned_to_open",
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_cart(
        self,
        cart: Cart,
        target: str,
        **extras: Any,
    ) -> Decision:
        """Decide using the cart's own status as the current state."""
        current = cart.cart_status or self.initial_state
        return self.decide(current, target, cart, **extras)

    def is_final(self, state: str) -> bool:
        """Completed or canceled — no more line-item changes."""
        return self.normalize(state) in {"completed", "canceled"}

    def is_active(self, cart: Cart) -> bool:
        """A cart that's still being built or waiting on something."""
        return self.normalize(cart.cart_status or "") in {
            "open",
            "pending",
            "checkout",
            "partial",
        }

    def is_cancellable(self, cart: Cart) -> bool:
        return cancellable(cart)

    def is_checkout_pending(self, cart: Cart) -> bool:
        """Invoice issued, fulfilment not yet resolved."""
        return self.normalize(cart.cart_status or "") == "checkout"

    def is_fulfillable(self, cart: Cart) -> bool:
        """Checkout or partial — fulfilment is in progress."""
        return self.normalize(cart.cart_status or "") in {
            "checkout",
            "partial",
        }

    # ── Error mapping ────────────────────────────────────────────────

    def transition_error(self, decision: Decision) -> Exception:
        return ValueError(
            f"Illegal cart transition '{decision.current}' → "
            f"'{decision.target}': {decision.reason}"
        )

    def invalid_state_error(self, state: str) -> Exception:
        return ValueError(
            f"Invalid cart status '{state}'. "
            f"Valid: {sorted(self.valid_states)}"
        )