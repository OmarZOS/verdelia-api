# policies/delivery_policy.py
"""
DeliveryPolicy — state rules for the Delivery lifecycle.

States (from the DB enum `delivery_status`):
    pending, processing, confirmed, shipped, in_transit,
    out_for_delivery, delivered, failed, cancelled, returned, refunded

Transitions (from the schema diagram):
    pending          → processing
    processing       → confirmed
    confirmed        → shipped
    shipped          → in_transit
    in_transit       → out_for_delivery
    out_for_delivery → delivered
    delivered        → returned
    delivered        → refunded

    pending          → cancelled
    processing       → cancelled
    confirmed        → cancelled
    shipped          → cancelled

    processing       → failed
    in_transit       → failed
    out_for_delivery → failed
    failed           → returned

Predicates split into three families:

  - Structural: read a column on the Delivery. A delivery without a
    destination cannot leave `pending`. A delivery with no provider
    cannot be `shipped`. These are the invariants that make the state
    meaningful.

  - Signal: require an explicit keyword from the caller to confirm an
    event that happened outside the database (carrier accepted,
    proof-of-delivery captured, refund issued). Defaults are `False`
    so a caller who forgets to assert the event gets a denial, not a
    silent pass.

  - Business: express a rule that is local to the delivery, like
    "only cancellable before shipment". These are also enforced.
"""

import logging
from typing import Any

from core.models.models import Delivery

from policies.transitions import (
    Decision,
    PolicyBase,
    Transition,
    TransitionRegistry,
    always,
)

from core.logging_config import get_logger

logger = get_logger(__name__)



# ============================================================================
# STRUCTURAL PREDICATES — read the delivery
# ============================================================================

def has_recipient(delivery: Delivery) -> bool:
    """
    A delivery is only meaningful if it has somewhere to go. Required
    before the delivery leaves `pending`: without a recipient or an
    address, the delivery has no business being processed.
    """
    return bool(
        # (delivery.recipient_person or 0) > 0
        (delivery.recipient_provider or 0) > 0
        or (delivery.delivery_address_id or 0) > 0
        or (delivery.delivery_current_address_id or 0) > 0
    )


def has_provider(delivery: Delivery) -> bool:
    """
    A delivery cannot be shipped without a provider attached. This is
    the supplier that owns the goods and hands them to the carrier.
    """
    return (delivery.delivery_provider_id or 0) > 0

def has_broker(delivery: Delivery) -> bool:
    """
    A delivery cannot be shipped without a provider attached. This is
    the supplier that owns the goods and hands them to the carrier.
    """
    return (delivery.delivery_broker_id or 0) > 0


def has_packages(delivery: Delivery) -> bool:
    """
    A delivery cannot leave `processing` without at least one package
    declared. Package count is what turns an abstract "delivery" into
    something a carrier can physically pick up.
    """

    
    logger.info(f"Package count: {delivery.delivery_package_count}")

    logger.info(f"id_delivery: {delivery.id_delivery}")
    logger.info(f"recipient_person: {delivery.recipient_person}")
    logger.info(f"recipient_provider: {delivery.recipient_provider}")
    logger.info(f"delivery_package_count: {delivery.delivery_package_count}")
    logger.info(f"delivery_total_weight: {delivery.delivery_total_weight}")
    logger.info(f"delivery_cargo_dimensions: {delivery.delivery_cargo_dimensions}")
    logger.info(f"delivery_goods_description: {delivery.delivery_goods_description}")
    logger.info(f"hs_code: {delivery.hs_code}")
    logger.info(f"delivery_merchant_name: {delivery.delivery_merchant_name}")
    logger.info(f"delivery_shipping_method: {delivery.delivery_shipping_method}")
    logger.info(f"delivery_special_instructions: {delivery.delivery_special_instructions}")
    logger.info(f"delivery_created_at: {delivery.delivery_created_at}")
    logger.info(f"delivery_updated_at: {delivery.delivery_updated_at}")
    logger.info(f"delivery_status: {delivery.delivery_status}")
    logger.info(f"delivery_address_id: {delivery.delivery_address_id}")
    logger.info(f"delivery_current_address_id: {delivery.delivery_current_address_id}")
    logger.info(f"delivery_fee: {delivery.delivery_fee}")
    logger.info(f"delivery_provider_id: {delivery.delivery_provider_id}")
    logger.info(f"delivery_broker_id: {delivery.delivery_broker_id}")
    logger.info(f"delivery_invoice_ref: {delivery.delivery_invoice_ref}")
    logger.info(f"delivery_source_type: {delivery.delivery_source_type}")
    logger.info(f"delivery_source_id: {delivery.delivery_source_id}")



    return (delivery.delivery_package_count or 0) > 0


def has_positive_weight(delivery: Delivery) -> bool:
    """
    A declared weight is what the carrier bills against. Zero or
    missing weight on a delivery is a sign the packing step never
    finished.
    """
    return (delivery.delivery_total_weight or 0) > 0


def has_shipping_method(delivery: Delivery) -> bool:
    """
    The delivery must have a shipping method chosen. Defaults to
    `'standard'` at creation, so in practice this is always true — but
    if a caller ever blanks the field, the transition is refused.
    """
    method = (delivery.delivery_shipping_method or "").strip()
    return method != ""


def is_cancellable_window(delivery: Delivery) -> bool:
    """
    Cancellation is a business decision that is only legal before the
    goods are moving. Once `shipped`, the path out is `failed` →
    `returned`, not `cancelled`.
    """
    status = (delivery.delivery_status or "").lower()
    return status in {"pending", "processing", "confirmed"}


# ============================================================================
# SIGNAL PREDICATES — require an explicit caller assertion
# ============================================================================
#
# These represent facts that are true in the world but not in the
# database row. The caller asserts them; the policy refuses to guess.
# Default is False so a forgotten signal is a denial, not a pass.

def carrier_accepted(
    delivery: Delivery, *, delivery_confirmed: bool = False
) -> bool:
    """confirmed → shipped: the carrier picked up the goods."""
    return delivery_confirmed


def in_transit_acknowledged(
    delivery: Delivery, *, in_transit_acknowledged: bool = False
) -> bool:
    """shipped → in_transit: the carrier's tracking shows movement."""
    return in_transit_acknowledged


def proof_captured(
    delivery: Delivery, *, proof_captured: bool = False
) -> bool:
    """out_for_delivery → delivered: signed receipt / photo / scan."""
    return proof_captured


def incident_reported(
    delivery: Delivery, *, incident_reported: bool = False
) -> bool:
    """
    * → failed: an operations user has filed an incident. Not a
    signal the workflow should invent; someone has to say so.
    """
    return incident_reported


def return_confirmed(
    delivery: Delivery, *, return_confirmed: bool = False
) -> bool:
    """delivered/failed → returned: goods came back to origin."""
    return return_confirmed


def refund_completed(
    delivery: Delivery, *, refund_completed: bool = False
) -> bool:
    """delivered → refunded: the finance side has issued the refund."""
    return refund_completed


# ============================================================================
# POLICY
# ============================================================================

class DeliveryPolicy(PolicyBase):
    """Delivery status rules."""

    def _build_registry(self) -> TransitionRegistry:
        registry = TransitionRegistry(
            valid_states={
                "pending",
                "processing",
                "confirmed",
                "shipped",
                "in_transit",
                "out_for_delivery",
                "delivered",
                "failed",
                "cancelled",
                "returned",
                "refunded",
            },
            initial_state="pending",
            # Terminal: nothing leaves these. `delivered` and `failed`
            # still have outgoing edges (returned / refunded), so they
            # are not in this set.
            terminal_states={"cancelled", "returned", "refunded"},
            normalize=lambda s: (s or "pending").lower(),
        )

        registry.add_many([
            # ── pending ─────────────────────────────────────────────
            Transition(
                source="pending", target="processing",
                # Structural only: a recipient is required. No signal.
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
                # Structural: a recipient AND a package count are
                # required. A delivery with no packages is still an
                # abstraction, not something a carrier can handle.
                predicate=lambda d: has_recipient(d) and has_packages(d),
                side_effects=("assign_provider",),
                name="processing_to_confirmed",
            ),
            Transition(
                source="processing", target="failed",
                # Signal: someone has to file the incident.
                predicate=incident_reported,
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
                # Signal + structural: the carrier accepted AND there
                # is a provider on the delivery. You cannot ship goods
                # nobody owns.
                predicate=lambda d, **kw: (
                    has_broker(d) and has_provider(d) and carrier_accepted(d, **kw)
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

            # ── shipped ─────────────────────────────────────────────
            Transition(
                source="shipped", target="in_transit",
                predicate=in_transit_acknowledged,
                side_effects=("notify_recipient",),
                name="shipped_to_in_transit",
            ),
            # Cancellation is deliberately NOT allowed from `shipped`.
            # Once in motion, the path out is `failed` → `returned`.

            # ── in_transit ──────────────────────────────────────────
            Transition(
                source="in_transit", target="out_for_delivery",
                # Structural: the delivery must still have a
                # destination. Guards against a reroute that never
                # completed.
                predicate=has_recipient,
                side_effects=("notify_recipient",),
                name="in_transit_to_out_for_delivery",
            ),
            Transition(
                source="in_transit", target="failed",
                predicate=incident_reported,
                side_effects=("notify_recipient",),
                name="in_transit_to_failed",
            ),

            # ── out_for_delivery ────────────────────────────────────
            Transition(
                source="out_for_delivery", target="delivered",
                predicate=proof_captured,
                side_effects=(
                    "confirm_inventory",
                    "advance_order_to_delivered",
                    "notify_recipient",
                ),
                name="out_for_delivery_to_delivered",
            ),
            Transition(
                source="out_for_delivery", target="failed",
                predicate=incident_reported,
                side_effects=("notify_recipient",),
                name="out_for_delivery_to_failed",
            ),

            # ── delivered ───────────────────────────────────────────
            Transition(
                source="delivered", target="returned",
                predicate=return_confirmed,
                side_effects=("release_inventory",),
                name="delivered_to_returned",
            ),
            Transition(
                source="delivered", target="refunded",
                predicate=refund_completed,
                side_effects=(),
                name="delivered_to_refunded",
            ),

            # ── failed ──────────────────────────────────────────────
            Transition(
                source="failed", target="returned",
                predicate=return_confirmed,
                side_effects=("release_inventory",),
                name="failed_to_returned",
            ),
        ])

        return registry

    # ── Convenience ──────────────────────────────────────────────────

    def decide_for_delivery(
        self, delivery: Delivery, target: str, **extras: Any
    ) -> Decision:
        current = delivery.delivery_status or self.initial_state
        return self.decide(current, target, delivery, **extras)

    def is_cancellable(self, delivery: Delivery) -> bool:
        return is_cancellable_window(delivery)

    # ── Error mapping ────────────────────────────────────────────────

    def transition_error(self, decision: Decision) -> Exception:
        return ValueError(
            f"Illegal delivery transition '{decision.current}' → "
            f"'{decision.target}': {decision.reason}"
        )

    def invalid_state_error(self, state: str) -> Exception:
        return ValueError(
            f"Invalid delivery status '{state}'. "
            f"Valid: {sorted(self.valid_states)}"
        )