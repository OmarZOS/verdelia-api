# services/action_link_service.py
"""
Action link service.

Owns one method per action plus the precondition checks. Uses
`FinanceServiceClient` for money operations and `DeliveryService`
for delivery state.

Nothing here touches the database directly. Every read and write
goes through the service that owns the model. The session, when a
service needs one, lives inside that service's repository.

Nothing here touches the nonce table — that's the workflow's
concern. This service performs the action; the workflow decides
whether it's allowed to run and whether to mark it spent.

Four actions:

  * `pay`                    — pay an invoice on the finance server
  * `authorize_charge`       — authorize a card charge against an
                               invoice on the finance server
  * `accept_delivery_change` — accept a proposed delivery state
                               change (local DB)
  * `receive_proposal`       — return a payload the sender embedded
                               in the token. No entity, no state
                               transition; the token *is* the
                               payload.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.helpers.auth.link_dependencies import LinkPayload
from core.exceptions.handler import APIException
from services.delivery_service import DeliveryService
from storage.wrappers.finance_client import FinanceServiceClient

logger = logging.getLogger(__name__)


# The four actions this service handles. Named here so the router,
# the workflow, and this file all reference the same strings.
ACTION_PAY = "pay"
ACTION_AUTHORIZE_CHARGE = "authorize_charge"
ACTION_ACCEPT_DELIVERY_CHANGE = "accept_delivery_change"
ACTION_RECEIVE_PROPOSAL = "receive_proposal"

SUPPORTED_ACTIONS = frozenset({
    ACTION_PAY,
    ACTION_AUTHORIZE_CHARGE,
    ACTION_ACCEPT_DELIVERY_CHANGE,
    ACTION_RECEIVE_PROPOSAL,
})


class ActionLinkService:
    """Executes the actions a link token authorizes."""

    def __init__(
        self,
        finance_client: Optional[FinanceServiceClient] = None,
        delivery_service: Optional[DeliveryService] = None,
    ):
        self.finance = finance_client or FinanceServiceClient()
        self.deliveries = delivery_service or DeliveryService()

    # ══════════════════════════════════════════════════════════════
    # Precondition checks
    # ══════════════════════════════════════════════════════════════

    async def assert_action_viable(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action: str,
    ) -> None:
        """Ensure the entity exists and the action makes sense.

        Called at create time (so we don't issue a link that will
        fail) and at redeem time (so we don't act on an entity
        whose state changed since the link was issued).

        `receive_proposal` has no entity to check — the payload is
        self-contained, so the precondition is trivially satisfied.
        """
        if action in (ACTION_PAY, ACTION_AUTHORIZE_CHARGE):
            await self._assert_invoice_payable(entity_id)
            return

        if action == ACTION_ACCEPT_DELIVERY_CHANGE:
            self._assert_delivery_has_pending_change(entity_id)
            return

        if action == ACTION_RECEIVE_PROPOSAL:
            # Nothing to check. The token carries its own payload.
            return

        raise APIException(
            status_code=400,
            error_code="UNSUPPORTED_ACTION",
            message=f"Unknown action: {action!r}",
        )

    async def _assert_invoice_payable(self, invoice_id: int) -> None:
        """The invoice exists on the finance side and is payable.

        Invoices live on the finance server, not locally. The
        finance client is how we ask about one. A 404 from the
        client means the invoice doesn't exist; a paid or cancelled
        status means it can't be paid.
        """
        try:
            summary = await self.finance.get_invoice_payments(invoice_id)
        except Exception as e:
            msg = str(e).lower()
            if "not found" in msg or "404" in msg:
                raise APIException(
                    status_code=404,
                    error_code="INVOICE_NOT_FOUND",
                    message=f"Invoice {invoice_id} not found",
                )
            raise

        if summary.status in ("paid", "canceled", "refunded"):
            raise APIException(
                status_code=409,
                error_code="INVOICE_NOT_PAYABLE",
                message=(
                    f"Invoice {invoice_id} is {summary.status}; "
                    f"it cannot be paid"
                ),
            )

    def _assert_delivery_has_pending_change(
        self, delivery_id: int,
    ) -> None:
        """The delivery exists and has a pending state change."""
        delivery = self.deliveries.get_by_id(delivery_id)

        if delivery.pending_state_change is None:
            raise APIException(
                status_code=409,
                error_code="NO_PENDING_STATE_CHANGE",
                message=(
                    f"Delivery {delivery_id} has no pending state "
                    f"change to accept"
                ),
            )

    # ══════════════════════════════════════════════════════════════
    # Dispatch
    # ══════════════════════════════════════════════════════════════

    async def dispatch(
        self,
        *,
        claims: LinkPayload,
        idempotency_key: Optional[str],
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Route the action to the matching handler.

        Each handler calls one or more services. The dispatch is
        the only place the action string is matched — adding a new
        action means adding a branch here and one handler method.
        """
        if claims.action == ACTION_PAY:
            return await self._handle_pay_invoice(
                claims=claims, notes=notes,
            )

        if claims.action == ACTION_AUTHORIZE_CHARGE:
            return await self._handle_authorize_charge(
                claims=claims, notes=notes,
            )

        if claims.action == ACTION_ACCEPT_DELIVERY_CHANGE:
            return await self._handle_accept_delivery_change(
                claims=claims, notes=notes,
            )

        if claims.action == ACTION_RECEIVE_PROPOSAL:
            return await self._handle_receive_proposal(
                claims=claims, notes=notes,
            )

        raise APIException(
            status_code=400,
            error_code="UNSUPPORTED_ACTION",
            message=f"Unknown action: {claims.action!r}",
        )

    # ══════════════════════════════════════════════════════════════
    # Handlers — entity-backed
    # ══════════════════════════════════════════════════════════════

    async def _handle_pay_invoice(
        self,
        *,
        claims: LinkPayload,
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Pay an invoice via the finance client.

        The invoice's remaining balance is authoritative for the
        amount. The link carries no amount — that comes from the
        invoice on the finance side.
        """
        from core.models.finance_models import PaymentCreate

        summary = await self.finance.get_invoice_payments(
            claims.entity_id
        )
        amount = float(summary.remaining_amount)

        if amount <= 0:
            raise APIException(
                status_code=409,
                error_code="INVOICE_ALREADY_PAID",
                message="Invoice has no remaining balance",
            )

        payment = await self.finance.create_payment(PaymentCreate(
            invoice_id=claims.entity_id,
            amount=amount,
            payment_method="wallet",
            user_id=claims.issued_to or 0,
            notes=notes or "Paid via link",
            payment_type="payment",
        ))

        confirmed = await self.finance.confirm_payment(
            payment_id=payment.id,
            transaction_details={"user_id": claims.issued_to},
        )

        return {
            "payment_id": confirmed.id,
            "invoice_id": confirmed.invoice_id,
            "amount": confirmed.amount,
            "status": confirmed.status,
        }

    async def _handle_authorize_charge(
        self,
        *,
        claims: LinkPayload,
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Authorize a card charge against an invoice.

        Creates the payment on the finance side but does not
        confirm it. Confirmation comes from the card processor's
        webhook, or from a separate authorize call the client makes
        once 2FA succeeds.
        """
        from core.models.finance_models import PaymentCreate

        summary = await self.finance.get_invoice_payments(
            claims.entity_id
        )
        amount = float(summary.remaining_amount)

        payment = await self.finance.create_payment(PaymentCreate(
            invoice_id=claims.entity_id,
            amount=amount,
            payment_method="card",
            user_id=claims.issued_to or 0,
            notes=notes or "Card charge authorized via link",
            payment_type="payment",
        ))

        return {
            "payment_id": payment.id,
            "invoice_id": payment.invoice_id,
            "amount": payment.amount,
            "status": "pending_authorization",
            "next_step": (
                "The card processor will confirm or decline this "
                "charge. No further action is required."
            ),
        }

    async def _handle_accept_delivery_change(
        self,
        *,
        claims: LinkPayload,
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Accept a proposed delivery state change.

        Delegates to `DeliveryService.accept_pending_state_change`,
        which owns the transition. The service returns a dict
        describing what changed.
        """
        return self.deliveries.accept_pending_state_change(
            delivery_id=claims.entity_id,
            notes=notes,
        )

    # ══════════════════════════════════════════════════════════════
    # Handlers — payload carrier
    # ══════════════════════════════════════════════════════════════

    async def _handle_receive_proposal(
        self,
        *,
        claims: LinkPayload,
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Return a payload the sender embedded in the token.

        No entity lookup, no state transition. The token carries
        the proposal; this handler hands it back so the recipient
        can read it and decide what to do next. The API doesn't
        validate the payload, doesn't store it, and doesn't act on
        it.

        What "accept" means is the recipient's app's decision.
        For a money proposal, the recipient would call the finance
        server directly. For a delivery proposal, they'd call the
        delivery endpoint. This handler is the read side of a
        message, not the write side of a transaction.
        """
        return {
            "proposal": claims.extra or {},
            "from_user_id": claims.issued_to,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }