# workflows/payment_workflows.py
"""
Payment workflows — orchestration gated by PaymentPolicy.

Status changes go through `PaymentPolicy.decide_for_payment()`. The
workflow never assigns `payment_status`; it asks the policy for a
Decision, then asks the service to persist the target.

Wallet id resolution:
  * `create_payment` receives `user_id`; the payer wallet is taken
    from `payment_payer_wallet_id` when present, otherwise resolved
    from the user. Never falls back to the system wallet.
  * `confirm` re-resolves the wallet from the payment row's owner
    so a retry hits the same account.
  * `settle_qr` carries an explicit `payer_wallet_id`.

Money rule: a wallet payment cannot reach `completed` without a
ledger entry. The transfer leg runs first; if it fails, the payment
is cancelled (policy permits any non-terminal → cancelled) and the
error propagates.
"""

from __future__ import annotations

from typing import Optional

from core.exceptions.handler import APIException
from core.logging_config import get_logger
from core.messages.error_codes import ErrorCode
from core.messages.http_status import HTTP_502_BAD_GATEWAY
from core.models.api_models import Payment_API
from core.models.models import Payment
from policies.payment_policy import PaymentPolicy
from services.financial_service import FinancialService
from services.user_service import UserService
from workflows.wallet_workflow import WalletWorkflow

logger = get_logger(__name__)


INSTANT_SETTLE_METHODS = {"wallet"}


class PaymentWorkflow:
    def __init__(
        self,
        financial_service: Optional[FinancialService] = None,
        user_service: Optional[UserService] = None,
        wallet_workflow: Optional[WalletWorkflow] = None,
        policy: Optional[PaymentPolicy] = None,
    ):
        self.financial_service = financial_service or FinancialService()
        self.user_service = user_service or UserService()
        self.wallets = wallet_workflow or WalletWorkflow()
        self.policy = policy or PaymentPolicy()

    # ------------------------------------------------------------------ #
    # Creation
    # ------------------------------------------------------------------ #

    async def create_payment(
        self,
        payment_data: Payment_API,
        user_id: int,
    ) -> Payment:
        created = self.financial_service.create_payment(payment_data)

        method = (payment_data.payment_method or "").strip().lower()
        if method in INSTANT_SETTLE_METHODS:
            payer_wallet_id = self._resolve_payer_wallet(
                payment_data, user_id,
            )
            created = await self._settle_via_wallet(
                created, payment_data, payer_wallet_id,
            )
        return created

    async def _settle_via_wallet(
        self,
        payment: Payment,
        payment_data: Payment_API,
        payer_wallet_id: int,
    ) -> Payment:
        # 1) Money leg first. A status flip without a ledger entry
        #    is an accounting bug.
        try:
            await self._transfer_for_payment(
                payment, payment_data, payer_wallet_id,
            )
        except Exception:
            logger.exception(
                "Wallet leg failed for payment %s; cancelling",
                payment.payment_id,
            )
            # Policy: any non-terminal → cancelled is allowed.
            self._transition_best_effort(payment, "cancelled")
            raise

        # 2) Legal chain to completed, gated by the policy.
        payment = self._transition_or_raise(payment, "processing")
        payment = self._transition_or_raise(
            payment, "completed",
            expected_amount=float(payment.payment_amount or 0),
        )
        return payment

    # ------------------------------------------------------------------ #
    # Confirmation
    # ------------------------------------------------------------------ #

    async def confirm(self, payment_id: int) -> Optional[Payment]:
        payment = self.financial_service.get_payment_by_id(payment_id)
        if payment is None:
            return None

        method = (payment.payment_method or "").strip().lower()
        if method in INSTANT_SETTLE_METHODS:
            payment_api = _as_payment_api(payment)
            payer_wallet_id = self._resolve_confirm_wallet(
                payment, payment_api,
            )
            # Retry the money leg before any status change. If the
            # original attempt left the payment pending, this is the
            # only opportunity to pair `completed` with a ledger row.
            await self._transfer_for_payment(
                payment, payment_api, payer_wallet_id,
            )

        current = (payment.payment_status or "").lower()
        if current == "pending":
            payment = self._transition_or_raise(payment, "processing")
        return self._transition_or_raise(
            payment, "completed",
            expected_amount=float(payment.payment_amount or 0),
        )

    # ------------------------------------------------------------------ #
    # QR settlement
    # ------------------------------------------------------------------ #

    async def settle_qr(
        self,
        *,
        invoice_id: int,
        amount: float,
        currency: str,
        payer_wallet_id: int,
        payee_wallet_id: Optional[int] = None,
        payer_user_id: Optional[int] = None,
        reference: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Payment:
        if not payer_wallet_id:
            raise APIException(
                status_code=HTTP_502_BAD_GATEWAY,
                error_code=ErrorCode.WALLET_NOT_FOUND,
                details={"reason": "QR settlement requires payer_wallet_id"},
            )

        payment_data = Payment_API(
            payment_invoice_id=invoice_id,
            payment_amount=amount,
            payment_method="wallet",
            payment_status="pending",
            payment_reference=reference,
            payment_notes=notes,
            payment_payer_wallet_id=payer_wallet_id,
            payment_payee_wallet_id=payee_wallet_id,
        )
        # The QR already carries the payer wallet; `user_id` is only
        # consulted when the wallet is missing, which it isn't here.
        return await self.create_payment(
            payment_data, user_id=payer_user_id or 0,
        )

    # ------------------------------------------------------------------ #
    # Policy-gated transitions
    # ------------------------------------------------------------------ #

    def _transition_or_raise(
        self,
        payment: Payment,
        target: str,
        **extras,
    ) -> Payment:
        """
        Ask the policy, then persist the target. Raises on denial.
        """
        decision = self.policy.decide_for_payment(
            payment, target=target, **extras,
        )
        if not decision.allowed:
            raise self.policy.transition_error(decision)

        return self.financial_service.apply_payment_status(
            payment, decision.target, reason=decision.reason,
        )

    def _transition_best_effort(
        self,
        payment: Payment,
        target: str,
        **extras,
    ) -> None:
        """
        Ask the policy and persist if allowed; log if not. Used only
        on cleanup paths where we must not mask the original error.
        """
        try:
            decision = self.policy.decide_for_payment(
                payment, target=target, **extras,
            )
            if not decision.allowed:
                logger.error(
                    "Policy denied %s → %s for payment %s: %s",
                    payment.payment_status, target,
                    payment.payment_id, decision.reason,
                )
                return
            self.financial_service.apply_payment_status(
                payment, decision.target, reason=decision.reason,
            )
        except Exception:
            logger.exception(
                "Best-effort %s transition failed for payment %s",
                target, payment.payment_id,
            )

    # ------------------------------------------------------------------ #
    # Wallet leg
    # ------------------------------------------------------------------ #

    def _resolve_payer_wallet(
        self,
        payment_data: Payment_API,
        user_id: int,
    ) -> int:
        """
        Prefer the explicit wallet on the payload; fall back to the
        user's wallet. Never falls back to the system wallet.
        """
        explicit = getattr(payment_data, "payment_payer_wallet_id", None)
        if explicit:
            return int(explicit)

        wallet = self.user_service.get_wallet_by_user_id(user_id)
        if wallet is None:
            raise APIException(
                status_code=HTTP_502_BAD_GATEWAY,
                error_code=ErrorCode.WALLET_NOT_FOUND,
                details={
                    "reason": "payer wallet could not be resolved",
                    "user_id": user_id,
                },
            )
        return int(getattr(wallet, "id", wallet))

    def _resolve_confirm_wallet(
        self,
        payment: Payment,
        payment_api: Payment_API,
    ) -> int:
        stored = getattr(payment, "payment_payer_wallet_id", None)
        if stored:
            return int(stored)

        explicit = getattr(payment_api, "payment_payer_wallet_id", None)
        if explicit:
            return int(explicit)

        owner_user_id = getattr(payment, "payment_payer_user_id", None)
        if owner_user_id:
            wallet = self.user_service.get_wallet_by_user_id(owner_user_id)
            wallet_id = getattr(wallet, "id", wallet)
            if wallet_id is not None:
                return int(wallet_id)

        raise APIException(
            status_code=HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.WALLET_NOT_FOUND,
            details={
                "reason": "cannot resolve payer wallet on confirm",
                "payment_id": getattr(payment, "payment_id", None),
            },
        )

    async def _transfer_for_payment(
        self,
        payment: Payment,
        payment_data: Payment_API,
        payer_wallet_id: int,
    ) -> None:
        """
        Fallback rules:
          * payer  ← explicit payload id, else resolved id. No system
                     fallback — a payment with no payer wallet raises.
          * payee  ← explicit payload id, else None. None means the
                     counterparty is external, so the operation is a
                     debit (no system-wallet transfer).
        """
        payer_explicit = getattr(
            payment_data, "payment_payer_wallet_id", None,
        )
        payer = int(payer_explicit) if payer_explicit else payer_wallet_id

        payee_explicit = getattr(
            payment_data, "payment_payee_wallet_id", None,
        )
        payee = int(payee_explicit) if payee_explicit else None

        reference = (
            payment_data.payment_reference
            or f"payment:{payment.payment_id}"
        )
        amount = float(payment.payment_amount or 0)
        intent = "payment"

        if payee is not None:
            await self.wallets.transfer_between_wallets(
                source_wallet_id=payer,
                destination_wallet_id=payee,
                amount=amount,
                intent=intent,
                reference=reference,
            )
            return

        if payer:
            await self.wallets.debit_wallet(
                wallet_id=payer,
                amount=amount,
                intent=intent,
                reference=reference,
                for_payment_id=payment.payment_id,
            )
            return

        raise APIException(
            status_code=HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.FINANCE_SERVER_ERROR,
            details={
                "reason": "wallet payment has no payer wallet",
                "payment_id": payment.payment_id,
            },
        )


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #

def _as_payment_api(payment: Payment) -> Payment_API:
    return Payment_API(
        payment_invoice_id=getattr(payment, "payment_invoice_id", None),
        payment_amount=float(payment.payment_amount or 0),
        payment_method=payment.payment_method,
        payment_status=payment.payment_status,
        payment_reference=getattr(payment, "payment_reference", None),
        payment_notes=getattr(payment, "payment_notes", None),
        payment_payer_wallet_id=getattr(
            payment, "payment_payer_wallet_id", None
        ),
        payment_payee_wallet_id=getattr(
            payment, "payment_payee_wallet_id", None
        ),
    )


payment_workflow = PaymentWorkflow()