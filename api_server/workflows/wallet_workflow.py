# workflows/wallet_workflow.py
"""
Wallet workflow.

The API's wallet operations go through the finance server. This
workflow:

  * resolves a wallet id from a user id (or provider id, or owner
    pair) by calling the finance client,
  * wraps credit / debit / transfer calls with the standard
    exception handling,
  * short-circuits the common "top up then use" pattern — the
    caller doesn't have to resolve, then credit, then verify the
    new balance; one method does it.

Nothing here owns a database session. The wallet is on the
finance server; this workflow composes the finance client and
translates its failures into API exceptions.

Ownership rules:
  * The API server calls this workflow for its own wallet
    endpoints.
  * Other workflows (cart, subscription) call it when they need to
    move money as part of their own sequence.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_502_BAD_GATEWAY,
)
from storage.wrappers.finance_client import FinanceServiceClient

logger = logging.getLogger(__name__)


class WalletWorkflow:
    """Coordinates wallet operations against the finance server.

    Constructed per-request; holds a reference to the finance
    client and nothing else. All methods are safe to call from a
    request path.
    """

    def __init__(
        self,
        finance_client: Optional[FinanceServiceClient] = None,
    ):
        self.finance = finance_client or FinanceServiceClient()

    # ══════════════════════════════════════════════════════════════
    # Reads
    # ══════════════════════════════════════════════════════════════

    async def get_wallet_for_user(
        self, user_id: int,
    ) -> Dict[str, Any]:
        """Return the wallet for a user.

        Raises 404 when the user has no wallet. The finance server
        returns a 404 in that case and this method translates it.
        """
        return await self._call(
            self.finance.get_user_wallet,
            user_id,
            not_found_message=f"No wallet for user {user_id}",
            action="get user wallet",
        )

    async def get_wallet_for_provider(
        self, provider_id: int,
    ) -> Dict[str, Any]:
        """Return the wallet for a provider.

        A provider without a wallet resolves to the system wallet
        (the finance server's default). This method returns
        whatever the finance server resolved — callers that need
        to know whether it was the provider's own wallet or the
        system wallet should compare `type` against `"system"`.
        """
        return await self._call(
            self.finance.get_provider_wallet,
            provider_id,
            not_found_message=f"No wallet for provider {provider_id}",
            action="get provider wallet",
        )

    async def get_wallet_by_owner(
        self,
        *,
        owner_type: str,
        owner_id: int,
    ) -> Dict[str, Any]:
        """Resolve a wallet from an (owner_type, owner_id) pair."""
        return await self._call(
            self.finance.get_wallet_by_owner,
            owner_type=owner_type,
            owner_id=owner_id,
            not_found_message=(
                f"No wallet for {owner_type} {owner_id}"
            ),
            action="resolve wallet by owner",
        )

    async def get_wallet_by_id(
        self, wallet_id: int,
    ) -> Dict[str, Any]:
        """Return the wallet with the given id."""
        return await self._call(
            self.finance.get_wallet_by_id,
            wallet_id,
            not_found_message=f"Wallet {wallet_id} not found",
            action="get wallet by id",
        )

    async def get_wallet_transactions(
        self,
        wallet_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """Return a wallet's ledger, newest first."""
        try:
            return await self.finance.get_wallet_transactions(
                wallet_id, limit=limit, offset=offset,
            )
        except Exception as e:
            logger.error(
                f"Failed to get transactions for wallet "
                f"{wallet_id}: {e}"
            )
            raise APIException(
                status_code=HTTP_502_BAD_GATEWAY,
                error_code=ErrorCode.FINANCE_SERVER_ERROR,
                details={
                    "action": "get wallet transactions",
                    "wallet_id": wallet_id,
                    "error": str(e),
                },
            )

    # ══════════════════════════════════════════════════════════════
    # Writes
    # ══════════════════════════════════════════════════════════════

    async def credit_wallet(
        self,
        *,
        wallet_id: int,
        amount: float,
        intent: str,
        reference: str,
        for_payment_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Credit a wallet by id.

        Raises 404 when the wallet doesn't exist. Raises 400 when
        the amount is not positive (the finance server enforces
        this; the workflow doesn't re-check).
        """
        amount = _validate_amount(amount)

        return await self._call(
            self.finance.transfer_between_wallets,
            source_wallet_id=1,
            destination_wallet_id=wallet_id,
            amount=amount,
            intent=intent,
            reference=reference,
            not_found_message=f"Wallet {wallet_id} not found",
            action="credit wallet",
        )

    async def debit_wallet(
        self,
        *,
        wallet_id: int,
        amount: float,
        intent: str,
        reference: str,
        for_payment_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Debit a wallet by id.

        Raises 404 when the wallet doesn't exist. Raises 409 when
        the balance is below the amount — the finance server
        returns "Insufficient wallet balance. Available: X" and
        this method translates it.
        """
        amount = _validate_amount(amount)

        return await self._call(
            self.finance.transfer_between_wallets,
            source_wallet_id=wallet_id,
            destination_wallet_id=1,
            amount=amount,
            intent=intent,
            reference=reference,
            not_found_message=f"Wallet {wallet_id} not found",
            action="debit wallet",
            conflict_on="insufficient",
        )

    async def transfer_between_wallets(
        self,
        *,
        source_wallet_id: int,
        destination_wallet_id: int,
        amount: float,
        intent: str,
        reference: str,
    ) -> Dict[str, Any]:
        """Move money between two wallets.

        Both sides are one operation on the finance side. A
        failure on either leaves both unchanged.
        """
        amount = _validate_amount(amount)

        if source_wallet_id == destination_wallet_id:
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.VALIDATION_ERROR,
                details={
                    "reason": (
                        "source and destination wallets must differ"
                    ),
                },
            )

        return await self._call(
            self.finance.transfer_between_wallets,
            source_wallet_id=source_wallet_id,
            destination_wallet_id=destination_wallet_id,
            amount=amount,
            intent=intent,
            reference=reference,
            not_found_message="Wallet not found",
            action="transfer between wallets",
            conflict_on="insufficient",
        )

    # ══════════════════════════════════════════════════════════════
    # Composite operations
    # ══════════════════════════════════════════════════════════════

    async def credit_user_wallet(
        self,
        *,
        user_id: int,
        amount: float,
        intent: str,
        reference: str,
        for_payment_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Resolve a user's wallet and credit it.

        The two-step form — resolve then credit — is the common
        case when the caller has a user id but not a wallet id.
        One method for both saves the caller from forgetting the
        first step.
        """
        wallet = await self.get_wallet_for_user(user_id)
        wallet_id = _extract_wallet_id(wallet)

        return await self.credit_wallet(
            wallet_id=wallet_id,
            amount=amount,
            intent=intent,
            reference=reference,
            for_payment_id=for_payment_id,
        )

    async def debit_user_wallet(
        self,
        *,
        user_id: int,
        amount: float,
        intent: str,
        reference: str,
        for_payment_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Resolve a user's wallet and debit it."""
        wallet = await self.get_wallet_for_user(user_id)
        wallet_id = _extract_wallet_id(wallet)

        return await self.debit_wallet(
            wallet_id=wallet_id,
            amount=amount,
            intent=intent,
            reference=reference,
            for_payment_id=for_payment_id,
        )

    async def ensure_balance(
        self,
        *,
        user_id: int,
        minimum: float,
        top_up_to: Optional[float] = None,
        reference: str = "auto-topup",
    ) -> Dict[str, Any]:
        """Top up a user's wallet if its balance is below a floor.

        Idempotent in spirit: if the balance is already sufficient,
        no credit call is made and the current wallet is returned.
        If a credit is needed, the wallet is funded to `top_up_to`
        (or to `minimum` when `top_up_to` is None).

        Used by test scenarios and by onboarding flows that need a
        wallet to have funds before a downstream operation. Not
        intended for end-user flows — the user-facing top-up
        endpoint takes an explicit amount and shows a payment
        screen.
        """
        wallet = await self.get_wallet_for_user(user_id)
        balance = _to_decimal(wallet.get("balance", 0))

        target = _to_decimal(minimum)
        if top_up_to is not None:
            target = _to_decimal(top_up_to)

        if balance >= target:
            logger.info(
                f"Wallet for user {user_id} has balance "
                f"{balance}, no top-up needed"
            )
            return wallet

        top_up_amount = float(target - balance)
        logger.info(
            f"Topping up wallet for user {user_id}: "
            f"{balance} → {target} (+{top_up_amount})"
        )

        wallet_id = _extract_wallet_id(wallet)
        await self.credit_wallet(
            wallet_id=wallet_id,
            amount=top_up_amount,
            intent="topup",
            reference=reference,
        )

        # Return the wallet state *after* the credit. The finance
        # server's credit response carries `balance_after` — the
        # caller can read it directly.
        return await self.get_wallet_for_user(user_id)

    # ══════════════════════════════════════════════════════════════
    # Internals
    # ══════════════════════════════════════════════════════════════

    async def _call(
        self,
        fn,
        *args,
        not_found_message: str,
        action: str,
        conflict_on: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Invoke a finance client method and translate its failures.

        The finance client raises a plain `Exception` with the
        server's error message. This method inspects the message
        and picks the right HTTP status for the API's response:

          * "not found"        → 404
          * "insufficient"     → 409 (when `conflict_on` is set)
          * everything else    → 502 (the finance server is the
                                     upstream that failed)

        The 502 default is deliberate: any unexpected failure from
        the finance server is an upstream problem from the API's
        perspective. The client is not the user; a 500 would blame
        the wrong layer.
        """
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            message = str(e)
            lower = message.lower()

            logger.error(
                f"Wallet workflow {action} failed: {message}"
            )

            if "not found" in lower:
                raise APIException(
                    status_code=HTTP_404_NOT_FOUND,
                    error_code=ErrorCode.WALLET_NOT_FOUND,
                    details={
                        "action": action,
                        "error": message,
                        **kwargs,
                    },
                )

            if (
                conflict_on == "insufficient"
                and "insufficient" in lower
            ):
                raise APIException(
                    status_code=HTTP_409_CONFLICT,
                    error_code=ErrorCode.INSUFFICIENT_BALANCE,
                    details={
                        "action": action,
                        "error": message,
                        **kwargs,
                    },
                )

            raise APIException(
                status_code=HTTP_502_BAD_GATEWAY,
                error_code=ErrorCode.FINANCE_SERVER_ERROR,
                details={
                    "action": action,
                    "error": message,
                    **kwargs,
                },
            )


# ══════════════════════════════════════════════════════════════════
# Module-level helpers
# ══════════════════════════════════════════════════════════════════

def _validate_amount(amount: float) -> float:
    """Normalize and validate a money amount.

    Rejects non-finite and non-positive values before they reach
    the finance server. The finance server enforces the same rule;
    catching it here saves a round-trip and produces a clearer
    error message.
    """
    if amount is None:
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "amount", "reason": "missing"},
        )
    try:
        dec = Decimal(str(amount))
    except Exception:
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            details={
                "field": "amount",
                "reason": "not a number",
                "value": amount,
            },
        )
    if not dec.is_finite():
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "amount", "reason": "not finite"},
        )
    if dec <= 0:
        raise APIException(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            details={
                "field": "amount",
                "reason": "must be positive",
                "value": amount,
            },
        )
    return float(dec)


def _extract_wallet_id(wallet: Dict[str, Any]) -> int:
    """Pull the wallet id out of a wallet response.

    The finance server's `WalletResponse` model emits the id as
    `id`. Older or alternative endpoints may emit `wallet_id`. Both
    are accepted; if neither is present the response is malformed
    and the caller gets a clear error rather than a `None` that
    propagates into a downstream request.
    """
    if not isinstance(wallet, dict):
        raise APIException(
            status_code=HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.FINANCE_SERVER_ERROR,
            details={
                "reason": "wallet response is not a dict",
                "type": type(wallet).__name__,
            },
        )
    wallet_id = wallet.get("id")
    if wallet_id is None:
        wallet_id = wallet.get("wallet_id")
    if wallet_id is None:
        raise APIException(
            status_code=HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.FINANCE_SERVER_ERROR,
            details={
                "reason": "wallet response has no id",
                "keys": sorted(wallet.keys()),
            },
        )
    try:
        return int(wallet_id)
    except (ValueError, TypeError):
        raise APIException(
            status_code=HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.FINANCE_SERVER_ERROR,
            details={
                "reason": "wallet id is not an int",
                "value": wallet_id,
            },
        )


def _to_decimal(value: Any) -> Decimal:
    """Coerce a value to Decimal for arithmetic.

    Decimal is used for money comparisons in `ensure_balance`
    because float arithmetic on balances drifts — 0.1 + 0.2 is not
    0.3. The finance server stores balances as DECIMAL(20, 8); the
    workflow mirrors that precision when comparing.
    """
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")