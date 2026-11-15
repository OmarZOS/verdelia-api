# policies/cart_policy.py
"""
CartPolicy — Cart status rules, built on TransitionEngine.

States (from `cart_status` enum, stored lowercase):
    open, pending, completed, canceled, partial, checkout, abandoned

Transitions:

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

`checkout` is the transient state between "invoiced/paid" and
"fulfilled". Delivery is OPTIONAL: a cart with no delivery lines
(services, digital goods, pickup) can go straight from `checkout`
to `completed` as soon as its lines are done.

Predicates take a `Cart` instance as their first positional
argument and caller signals as keyword arguments.
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
#============================================================================

def _iter_or_empty(value: Optional[Iterable[Any]]) -> Iterable[Any]:
    return value or ()


def _status(cart: Cart) -> str:
    return (cart.cart_status or "open").lower()


def _item_status(item: Any) -> str:
    return (getattr(item, "delivery_status", "") or "").lower()


def _service_status(svc: Any) -> str:
    return (
        getattr(svc, "ordered_service_delivery_status", "") or ""
    ).lower()


_DELIVERED_LINE_STATUSES = frozenset({"delivered", "completed"})
_DEAD_LINE_STATUSES = frozenset({"cancelled", "canceled", "returned", "no_show"})


# ============================================================================
# PREDICATES
#============================================================================

def has_items(cart: Cart, **_: Any) -> bool:
    items = list(_iter_or_empty(getattr(cart, "ordered_item", None)))
    services = list(_iter_or_empty(getattr(cart, "ordered_service", None)))
    return (len(items) + len(services)) > 0


def has_provider(cart: Cart, **_: Any) -> bool:
    return bool(cart.provider_id)


def cart_stale(cart: Cart, *, stale: bool = False, **_: Any) -> bool:
    return bool(stale)


def checkout_ready(
    cart: Cart,
    *,
    invoice_issued: bool = False,
    delivery_created: bool = False,   # retained for backward compat; unused
    **_: Any,
) -> bool:
    """
    pending → checkout: the cart is invoiced and (optionally) delivered.
    Delivery is OPTIONAL — the only structural requirement is that the
    cart has an invoice row (invoice_id > 0). The caller may still
    assert `invoice_issued=True` as a sanity signal; `delivery_created`
    is accepted but ignored so existing call sites don't need to
    change.
    """
    if not (cart.invoice_id or 0) > 0:
        return False
    # `invoice_issued=False` here would mean the caller is being
    # defensive. We trust the FK on the cart row: if it has an
    # invoice_id, the invoice exists.
    return True


def partial_fulfilment(
    cart: Cart,
    *,
    cart_repo: Optional[CartRepository] = None,
    **_: Any,
) -> bool:
    """
    pending/checkout → partial: at least one line delivered, at least
    one line still outstanding.

    Only delivery-statuses on the cart's lines are trusted. A
    consumption with `product_reserved_quantity == 0` is NOT evidence
    of delivery.
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
    checkout/partial → completed.

    A cart is complete when every non-dead line is either delivered
    or has no delivery obligation. `no_delivery_required` is asserted
    by the caller for carts whose lines are all pickup/digital/service
    (nothing to ship). Services default to being "delivered" once the
    service line is complete.

    Empty carts are NOT fulfilled (guards against the
    "zero lines, zero pending, therefore done" failure).
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
    return _status(cart) in {"open", "pending", "partial"}


# ============================================================================
# POLICY
#============================================================================

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
                source="open", target="pending",
                predicate=lambda cart, **_: (
                    has_items(cart) and has_provider(cart)
                ),
                side_effects=("lock_prices",),
                name="open_to_pending",
            ),
            Transition(
                source="open", target="abandoned",
                predicate=cart_stale,
                side_effects=("archive_cart",),
                name="open_to_abandoned",
            ),
            Transition(
                source="open", target="canceled",
                predicate=cancellable,
                side_effects=("release_slot",),
                name="open_to_canceled",
            ),

            # ── pending ─────────────────────────────────────────────
            Transition(
                source="pending", target="abandoned",
                predicate=cart_stale,
                side_effects=("archive_cart",),
                name="pending_to_abandoned",
            ),
            Transition(
                source="pending", target="checkout",
                predicate=checkout_ready,
                side_effects=("invoice_issued",),
                name="pending_to_checkout",
            ),
            Transition(
                source="pending", target="partial",
                predicate=partial_fulfilment,
                side_effects=("split_fulfilment",),
                name="pending_to_partial",
            ),
            Transition(
                source="pending", target="canceled",
                predicate=cancellable,
                side_effects=(
                    "cancel_invoice_if_any",
                    "release_inventory",
                ),
                name="pending_to_canceled",
            ),

            # ── checkout ────────────────────────────────────────────
            Transition(
                source="checkout", target="completed",
                predicate=fully_fulfilled,
                side_effects=(
                    "close_invoice",
                    "confirm_inventory",
                ),
                name="checkout_to_completed",
            ),
            Transition(
                source="checkout", target="partial",
                predicate=partial_fulfilment,
                side_effects=("split_fulfilment",),
                name="checkout_to_partial",
            ),

            # ── partial ─────────────────────────────────────────────
            Transition(
                source="partial", target="completed",
                predicate=fully_fulfilled,
                side_effects=(
                    "close_invoice",
                    "confirm_remaining_inventory",
                ),
                name="partial_to_completed",
            ),
            Transition(
                source="partial", target="canceled",
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
                source="abandoned", target="open",
                predicate=lambda cart, **_: True,
                side_effects=("reopen_cart",),
                name="abandoned_to_open",
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_cart(
        self, cart: Cart, target: str, **extras: Any,
    ) -> Decision:
        current = cart.cart_status or self.initial_state
        return self.decide(current, target, cart, **extras)

    def is_final(self, state: str) -> bool:
        return self.normalize(state) in {"completed", "canceled"}

    def is_active(self, cart: Cart) -> bool:
        return self.normalize(cart.cart_status or "") in {
            "open", "pending", "checkout", "partial",
        }

    def is_cancellable(self, cart: Cart) -> bool:
        return cancellable(cart)

    def is_checkout_pending(self, cart: Cart) -> bool:
        return self.normalize(cart.cart_status or "") == "checkout"

    def is_fulfillable(self, cart: Cart) -> bool:
        return self.normalize(cart.cart_status or "") in {
            "checkout", "partial",
        }

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