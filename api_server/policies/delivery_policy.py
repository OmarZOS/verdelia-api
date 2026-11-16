# policies/delivery_policy.py
"""
DeliveryPolicy — verification-backed state rules.

Every predicate reads persisted state through the workflow's
repositories. No caller-asserted booleans. The only way to enable a
transition is to record the real-world evidence as a row first
(tracking event, incident, proof-of-delivery, return, refund payment).
"""

import logging
from typing import Any

from core.models.models import Delivery

from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
)

logger = logging.getLogger(__name__)


# policies/delivery_policy.py — replace the verification block only

# ── Structural checks (read the Delivery row) ──────────────────────

def has_recipient(d: Delivery, wf: Any = None) -> bool:
    return bool(
        (d.recipient_person_id or 0) > 0
        or (d.address_id or 0) > 0
    )

def has_provider(d: Delivery, wf: Any = None) -> bool:
    return (d.delivery_provider_id or 0) > 0

def has_broker(d: Delivery, wf: Any = None) -> bool:
    return (d.delivery_broker_id or 0) > 0

def has_packages(d: Delivery, wf: Any = None) -> bool:
    return (d.delivery_package_count or 0) > 0

def has_positive_weight(d: Delivery, wf: Any = None) -> bool:
    return (d.delivery_total_weight or 0) > 0

def has_shipping_method(d: Delivery, wf: Any = None) -> bool:
    return (d.delivery_shipping_method or "").strip() != ""

def has_carrier(d: Delivery, wf: Any = None) -> bool:
    return (d.carrying_user_id or 0) > 0

def is_cancellable_window(d: Delivery, wf: Any = None) -> bool:
    return (d.delivery_status or "").lower() in {
        "pending", "processing", "confirmed",
    }

def has_destination(d: Delivery, wf: Any = None) -> bool:
    return (d.address_id or 0) > 0

def has_tracking_started(d: Delivery, wf: Any = None) -> bool:
    return (d.current_address_id or 0) > 0
def address_has_moved_off_destination(d: Delivery) -> bool:
    return (
        has_tracking_started(d)
        and (d.current_address_id or 0) != (d.address_id or 0)
    )

def arrived_at_destination(d: Delivery) -> bool:
    return (
        has_carrier(d)
        and has_destination(d)
        and (d.current_address_id or 0) == (d.address_id or 0)
    )


# ── Verification through existing repos ────────────────────────────

def incident_accountable(d: Delivery, wf: Any) -> bool:
    """
    Failure path verification.

    With no incident table, the verifiable signal that an incident can
    be reported is that a carrier is assigned and tracking has begun —
    someone is accountable for the delivery at this point. Before
    that, "failed" has no operational meaning (nothing to have failed).
    """
    return has_carrier(d) and has_tracking_started(d)

def carrier_assignment_exists(d: Delivery, wf: Any) -> bool:
    """A carrier is assigned to the delivery."""
    return has_carrier(d)

def in_transit_event_recorded(d: Delivery, wf: Any) -> bool:
    """Tracking address has left the origin."""
    return address_has_moved_off_destination(d)

def out_for_delivery_event_recorded(d: Delivery, wf: Any) -> bool:
    """Tracking address has been set and is not the destination yet."""
    return has_tracking_started(d) and not arrived_at_destination(d)

def proof_of_delivery_exists(d: Delivery, wf: Any) -> bool:
    """Carrier arrived at the destination address."""
    return arrived_at_destination(d)

def return_received(d: Delivery, wf: Any) -> bool:
    """
    Return verification.

    With no return table, the verifiable signal is that the tracking
    address has moved *off* the delivery address after the goods had
    arrived there — the shipment is in motion away from the
    destination. Combined with `has_carrier`, this means a return trip
    exists.
    """
    return has_carrier(d) and address_has_moved_off_destination(d)

def refund_payment_completed(d: Delivery, wf: Any) -> bool:
    """A completed refund payment exists on the linked invoice."""
    if not d.delivery_invoice_ref:
        return False
    try:
        return wf.financial_repo.has_completed_refund(d.delivery_invoice_ref)
    except Exception:
        logger.exception("refund check failed for delivery %s", d.id_delivery)
        return False

# ── Verification checks (read related rows via the workflow) ───────
#
# Signature: (delivery, wf) -> bool. `wf` is DeliveryWorkflow, which
# exposes `tracking_repo`, `incident_repo`, `proof_repo`,
# `return_repo`, `assignment_repo`, `financial_repo`.

def incident_is_open(d: Delivery, wf: Any) -> bool:
    try:
        return wf.incident_repo.has_open_incident(d.id_delivery)
    except Exception:
        logger.exception("incident check failed for delivery %s", d.id_delivery)
        return False

def carrier_assignment_exists(d: Delivery, wf: Any) -> bool:
    if not has_carrier(d):
        return False
    try:
        return wf.assignment_repo.is_accepted(d.id_delivery)
    except Exception:
        logger.exception("assignment check failed for delivery %s", d.id_delivery)
        return False

def in_transit_event_recorded(d: Delivery, wf: Any) -> bool:
    try:
        return wf.tracking_repo.has_event(d.id_delivery, "in_transit")
    except Exception:
        logger.exception("tracking check failed for delivery %s", d.id_delivery)
        return False

def out_for_delivery_event_recorded(d: Delivery, wf: Any) -> bool:
    try:
        return wf.tracking_repo.latest_event_type(d.id_delivery) == "out_for_delivery"
    except Exception:
        logger.exception("tracking check failed for delivery %s", d.id_delivery)
        return False

def proof_of_delivery_exists(d: Delivery, wf: Any) -> bool:
    try:
        return wf.proof_repo.has_valid_proof(d.id_delivery)
    except Exception:
        logger.exception("proof check failed for delivery %s", d.id_delivery)
        return False

def return_received(d: Delivery, wf: Any) -> bool:
    try:
        return wf.return_repo.has_received_return(d.id_delivery)
    except Exception:
        logger.exception("return check failed for delivery %s", d.id_delivery)
        return False

def refund_payment_completed(d: Delivery, wf: Any) -> bool:
    if not d.delivery_invoice_ref:
        return False
    try:
        return wf.financial_repo.has_completed_refund(d.delivery_invoice_ref)
    except Exception:
        logger.exception("refund check failed for delivery %s", d.id_delivery)
        return False


# ── Policy ─────────────────────────────────────────────────────────

class DeliveryPolicy(PolicyBase):
    """Delivery status rules, verification-backed."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                "pending", "processing", "confirmed", "shipped",
                "in_transit", "out_for_delivery", "delivered",
                "failed", "cancelled", "returned", "refunded",
            },
            initial_state="pending",
            terminal_states={"cancelled", "returned", "refunded"},
            normalize=lambda s: (s or "pending").lower(),
        )

        registry.add_many([
            # ── pending ─────────────────────────────────────────────
            Transition(
                source="pending", target="processing",
                predicate=has_recipient,
                side_effects=("prepare_dispatch",),
                name="pending_to_processing",
            ),
            Transition(
                source="pending", target="cancelled",
                predicate=is_cancellable_window,
                side_effects=("release_inventory",),
                name="pending_to_cancelled",
            ),

            # ── processing ──────────────────────────────────────────
            Transition(
                source="processing", target="confirmed",
                predicate=lambda d, wf: (
                    has_recipient(d)
                    and has_packages(d)
                    and has_positive_weight(d)
                    and has_shipping_method(d)
                ),
                side_effects=("assign_provider",),
                name="processing_to_confirmed",
            ),
            Transition(
                source="processing", target="failed",
                predicate=incident_is_open,
                side_effects=("notify_recipient",),
                name="processing_to_failed",
            ),
            Transition(
                source="processing", target="cancelled",
                predicate=is_cancellable_window,
                side_effects=("release_inventory",),
                name="processing_to_cancelled",
            ),

            # ── confirmed ───────────────────────────────────────────
            Transition(
                source="confirmed", target="shipped",
                predicate=lambda d, wf: (
                    has_broker(d)
                    and has_provider(d)
                    and carrier_assignment_exists(d, wf)
                ),
                side_effects=("advance_order_to_shipped",),
                name="confirmed_to_shipped",
            ),
            Transition(
                source="confirmed", target="cancelled",
                predicate=is_cancellable_window,
                side_effects=("release_inventory",),
                name="confirmed_to_cancelled",
            ),
            Transition(
                source="confirmed", target="out_for_delivery",
                # Fast-path for same_day / courier: needs an accepted
                # carrier but no intermediate shipped/in_transit
                # tracking. Recipient must still be present.
                predicate=lambda d, wf: (
                    has_recipient(d)
                    and carrier_assignment_exists(d, wf)
                ),
                side_effects=("notify_recipient",),
                name="confirmed_to_out_for_delivery",
            ),

            # ── shipped ─────────────────────────────────────────────
            Transition(
                source="shipped", target="in_transit",
                predicate=in_transit_event_recorded,
                side_effects=("notify_recipient",),
                name="shipped_to_in_transit",
            ),

            # ── in_transit ──────────────────────────────────────────
            Transition(
                source="in_transit", target="out_for_delivery",
                predicate=out_for_delivery_event_recorded,
                side_effects=("notify_recipient",),
                name="in_transit_to_out_for_delivery",
            ),
            Transition(
                source="in_transit", target="failed",
                predicate=incident_is_open,
                side_effects=("notify_recipient",),
                name="in_transit_to_failed",
            ),

            # ── out_for_delivery ────────────────────────────────────
            Transition(
                source="out_for_delivery", target="delivered",
                predicate=proof_of_delivery_exists,
                side_effects=(
                    "confirm_inventory",
                    "advance_order_to_delivered",
                    "notify_recipient",
                ),
                name="out_for_delivery_to_delivered",
            ),
            Transition(
                source="out_for_delivery", target="failed",
                predicate=incident_is_open,
                side_effects=("notify_recipient",),
                name="out_for_delivery_to_failed",
            ),

            # ── delivered ───────────────────────────────────────────
            Transition(
                source="delivered", target="returned",
                predicate=return_received,
                side_effects=("release_inventory",),
                name="delivered_to_returned",
            ),
            Transition(
                source="delivered", target="refunded",
                predicate=refund_payment_completed,
                side_effects=(),
                name="delivered_to_refunded",
            ),

            # ── failed ──────────────────────────────────────────────
            Transition(
                source="failed", target="returned",
                predicate=return_received,
                side_effects=("release_inventory",),
                name="failed_to_returned",
            ),
        ])

        return registry

    # ── Public API ──────────────────────────────────────────────────

    def decide_for_delivery(
        self, delivery: Delivery, target: str, wf: Any = None
    ) -> Decision:
        """
        Decide a delivery transition. `wf` is the workflow — passed
        through to verification predicates that read related rows.
        """
        current = delivery.delivery_status or self.initial_state
        return self.decide(current, target, delivery, wf=wf)

    def is_cancellable(self, delivery: Delivery) -> bool:
        return is_cancellable_window(delivery)