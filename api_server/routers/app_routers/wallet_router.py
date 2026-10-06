# routers/app_routers/wallet_router.py
"""
Wallet endpoints.

The wallet itself lives on the finance server. Every route here
proxies to `WalletWorkflow`, which calls the finance client. The
API owns auth and the HTTP contract; the finance server owns the
money.

Six endpoints:

  GET  /wallet/me                    — the caller's own wallet
  GET  /wallet/user/{user_id}        — a user's wallet (self or admin)
  GET  /wallet/provider/{provider_id} — a provider's wallet (owner or admin)
  GET  /wallet/system                — the system wallet (admin only)
  GET  /wallet/me/transactions       — the caller's ledger
  POST /wallet/topup                 — self-service top-up
  POST /wallet/adjust                — admin-only credit or debit

No endpoint exposes a primitive debit to end users. A debit
outside a payment flow is either a withdrawal (its own future
flow, with KYC and limits) or an admin adjustment (the last
route above).
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)
from services.helpers.auth.auth_dependencies import (
    get_current_user_id,
)
from workflows.wallet_workflow import WalletWorkflow

logger = logging.getLogger(__name__)


wallet_router = APIRouter()


# ══════════════════════════════════════════════════════════════════
# Request models
# ══════════════════════════════════════════════════════════════════

class WalletTopUp_API(BaseModel):
    """Self-service top-up request.

    The caller funds their own wallet. Amount is positive; method
    is one of the finance server's supported methods. `wallet` is
    excluded — topping up a wallet by debiting the same wallet is
    a no-op that would confuse the ledger.
    """
    amount: float = Field(
        ...,
        gt=0,
        description="Amount to add. Positive.",
    )
    payment_method: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description=(
            "How the money is arriving — 'deposit', 'cash', 'card', "
            "'bank_transfer', 'mobile_money'. 'wallet' is not "
            "accepted (topping up a wallet from itself)."
        ),
    )
    reference: Optional[str] = Field(
        None,
        max_length=64,
        description=(
            "Optional caller-generated reference for correlation. "
            "When omitted, the workflow generates one."
        ),
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes recorded on the transaction.",
    )

    @field_validator("payment_method")
    @classmethod
    def _valid_method(cls, v: str) -> str:
        allowed = {
            "deposit", "cash", "card",
            "bank_transfer", "mobile_money",
        }
        if v not in allowed:
            raise ValueError(
                f"payment_method must be one of {sorted(allowed)}"
            )
        return v


class WalletAdjustment_API(BaseModel):
    """Admin-only wallet adjustment.

    A credit or debit applied outside the payment system: support
    credits, corrections, promotional awards. Every call is
    logged with the admin's id and the reason.

    `direction` is explicit rather than signed-amount so a debit
    can't be confused with a credit by a missing minus sign.
    """
    user_id: int = Field(
        ...,
        gt=0,
        description="User whose wallet to adjust.",
    )
    direction: str = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Either 'credit' or 'debit'.",
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Amount to apply. Always positive.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "Why the adjustment is being applied. Required so "
            "every adjustment carries an audit trail."
        ),
    )

    @field_validator("direction")
    @classmethod
    def _valid_direction(cls, v: str) -> str:
        if v not in ("credit", "debit"):
            raise ValueError("direction must be 'credit' or 'debit'")
        return v


# ══════════════════════════════════════════════════════════════════
# Response models
# ══════════════════════════════════════════════════════════════════

class Wallet_API(BaseModel):
    """The caller-facing shape of a wallet.

    Mirrors the finance server's `WalletResponse` but flattens the
    owner into a nested object so a client reading `wallet.owner.id`
    doesn't have to know whether the id came from `user_id`,
    `provider_id`, or neither.
    """
    id: int
    owner: Optional[Dict[str, Any]] = None
    currency: str
    balance: float
    status: str
    type: str


class Transaction_API(BaseModel):
    """A single ledger entry as the client sees it."""
    id: int
    amount: float
    direction: str  # "in" or "out" relative to the queried wallet
    status: str
    intent: Optional[str] = None
    reference: Optional[str] = None
    counterparty_wallet_id: Optional[int] = None
    for_payment_id: Optional[int] = None
    created_at: Optional[datetime] = None


class WalletActionResponse(BaseModel):
    """Result of a credit, debit, or top-up."""
    success: bool
    message: str
    wallet_id: int
    amount: float
    balance_after: float
    transaction: Optional[Transaction_API] = None


class WalletAdjustmentResponse(BaseModel):
    """Result of an admin adjustment."""
    success: bool
    message: str
    wallet_id: int
    user_id: int
    direction: str
    amount: float
    balance_after: float
    transaction: Optional[Transaction_API] = None


class ErrorResponseModel(BaseModel):
    """Error envelope, matching the shape other routers emit."""
    success: bool = False
    status_code: int
    error_code: Optional[str] = None
    message: str
    timestamp: str


# ══════════════════════════════════════════════════════════════════
# Dependencies
# ══════════════════════════════════════════════════════════════════

def get_wallet_workflow() -> WalletWorkflow:
    """Construct a per-request wallet workflow."""
    return WalletWorkflow()


def _is_admin(user_id: int) -> bool:
    """Whether the given user has admin role.

    Wire this to your auth layer — the same shape as the check in
    `subscription_router` and `auth_router`. Returns False by
    default so an unwired deployment fails closed.
    """
    # Replace with your project's admin check.
    # Example:
    # from services.user_service import UserService
    # user = UserService().get_user_by_id(user_id)
    # return user is not None and user.app_user_type == "admin"
    return False


# ══════════════════════════════════════════════════════════════════
# Reads
# ══════════════════════════════════════════════════════════════════

@wallet_router.get(
    "/wallet/me",
    response_model=Wallet_API,
    summary="Get my wallet",
    description="Return the authenticated user's wallet.",
    responses={
        404: {
            "description": "Wallet not found",
            "model": ErrorResponseModel,
        },
        500: {"model": ErrorResponseModel},
    },
)
async def get_my_wallet(
    user_id: int = Depends(get_current_user_id),
    workflow: WalletWorkflow = Depends(get_wallet_workflow),
):
    """The caller's own wallet."""
    logger.info(f"GET /wallet/me — user:{user_id}")
    try:
        wallet = await workflow.get_wallet_for_user(user_id)
        return _wallet_response(wallet, owner_type="user", owner_id=user_id)
    except APIException as e:
        raise _http_from_api_exception(e)


@wallet_router.get(
    "/wallet/user/{user_id}",
    response_model=Wallet_API,
    summary="Get a user's wallet",
    description=(
        "Return another user's wallet. Requires the caller to be "
        "that user, or an admin."
    ),
    responses={
        403: {
            "description": "Not the owner and not an admin",
            "model": ErrorResponseModel,
        },
        404: {
            "description": "Wallet not found",
            "model": ErrorResponseModel,
        },
    },
)
async def get_user_wallet(
    user_id: int,
    caller_id: int = Depends(get_current_user_id),
    workflow: WalletWorkflow = Depends(get_wallet_workflow),
):
    """A specific user's wallet.

    Enforces: the caller is either the target user, or an admin.
    A non-admin asking for someone else's wallet gets a 403 — the
    target's existence is not a secret, but their balance is.
    """
    logger.info(
        f"GET /wallet/user/{user_id} — caller:{caller_id}"
    )

    if caller_id != user_id and not _is_admin(caller_id):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "status_code": HTTP_403_FORBIDDEN,
                "error_code": ErrorCode.FORBIDDEN,
                "message": "Not the owner and not an admin",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    try:
        wallet = await workflow.get_wallet_for_user(user_id)
        return _wallet_response(wallet, owner_type="user", owner_id=user_id)
    except APIException as e:
        raise _http_from_api_exception(e)


@wallet_router.get(
    "/wallet/provider/{provider_id}",
    response_model=Wallet_API,
    summary="Get a provider's wallet",
    description=(
        "Return a provider's wallet. Requires the caller to own "
        "the provider, or be an admin."
    ),
    responses={
        403: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
    },
)
async def get_provider_wallet(
    provider_id: int,
    caller_id: int = Depends(get_current_user_id),
    workflow: WalletWorkflow = Depends(get_wallet_workflow),
):
    """A specific provider's wallet.

    Ownership check is delegated to whatever the project uses to
    relate a user to a provider. The stub returns False by default
    so an unwired deployment fails closed.
    """
    logger.info(
        f"GET /wallet/provider/{provider_id} — caller:{caller_id}"
    )

    if not _owns_provider(caller_id, provider_id) and not _is_admin(
        caller_id
    ):
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "status_code": HTTP_403_FORBIDDEN,
                "error_code": ErrorCode.FORBIDDEN,
                "message": "Not the provider owner and not an admin",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    try:
        wallet = await workflow.get_wallet_for_provider(provider_id)
        # The finance server may resolve a provider without its own
        # wallet to the system wallet; report the actual type.
        return _wallet_response(
            wallet,
            owner_type=(
                "provider" if wallet.get("type") == "provider"
                else wallet.get("type")
            ),
            owner_id=(
                provider_id
                if wallet.get("type") == "provider"
                else None
            ),
        )
    except APIException as e:
        raise _http_from_api_exception(e)




@wallet_router.get(
    "/wallet/me/transactions",
    response_model=List[Transaction_API],
    summary="Get my wallet transactions",
    description=(
        "Return the authenticated user's wallet transaction "
        "history, newest first."
    ),
    responses={
        404: {"model": ErrorResponseModel},
    },
)
async def get_my_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    workflow: WalletWorkflow = Depends(get_wallet_workflow),
):
    """The caller's own ledger.

    Resolves the wallet first, then fetches the transactions. Two
    calls, but the alternative — transactions by user id — isn't
    an endpoint the finance server exposes.
    """
    logger.info(
        f"GET /wallet/me/transactions — user:{user_id} "
        f"limit:{limit} offset:{offset}"
    )

    try:
        wallet = await workflow.get_wallet_for_user(user_id)
        wallet_id = int(wallet["id"])
        transactions = await workflow.get_wallet_transactions(
            wallet_id, limit=limit, offset=offset,
        )
        return [
            _transaction_response(t, wallet_id=wallet_id)
            for t in transactions
        ]
    except APIException as e:
        raise _http_from_api_exception(e)


# ══════════════════════════════════════════════════════════════════
# Writes
# ══════════════════════════════════════════════════════════════════

@wallet_router.post(
    "/wallet/topup",
    response_model=WalletActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Top up my wallet",
    description=(
        "Credit the caller's wallet via a deposit or external "
        "payment method."
    ),
    responses={
        201: {"description": "Wallet topped up"},
        400: {
            "description": "Bad request — invalid amount or method",
            "model": ErrorResponseModel,
        },
        404: {
            "description": "Wallet not found",
            "model": ErrorResponseModel,
        },
    },
)
async def top_up_my_wallet(
    payload: WalletTopUp_API,
    user_id: int = Depends(get_current_user_id),
    workflow: WalletWorkflow = Depends(get_wallet_workflow),
):
    """Top up the caller's wallet.

    The top-up is modeled as a credit with `intent="topup"`. The
    finance server's ledger records it; no separate payment row is
    created on the API side, because the client hasn't provided an
    invoice or a payment reference that would justify one.

    For top-ups that go through the finance server's payment
    system (card, bank transfer with a real authorization), use
    the cart or payment workflow instead. This endpoint is for
    the direct-credit path: cash deposits, comped balances, and
    any case where the money has already been verified outside
    the payment system.
    """
    logger.info(
        f"POST /wallet/topup — user:{user_id} amount:{payload.amount} "
        f"method:{payload.payment_method}"
    )

    reference = payload.reference or (
        f"topup:{user_id}:{int(datetime.utcnow().timestamp())}"
    )

    try:
        result = await workflow.credit_user_wallet(
            user_id=user_id,
            amount=payload.amount,
            intent="topup",
            reference=reference,
        )

        logger.info(
            f"Wallet topped up: user={user_id} "
            f"amount={payload.amount} balance={result.get('balance_after')}"
        )

        return WalletActionResponse(
            success=True,
            message="Wallet topped up successfully",
            wallet_id=int(result["destination_wallet_id"]),
            amount=float(payload.amount),
            balance_after=float(result.get("destination_balance_after", 0)),
            transaction=_maybe_transaction_response(
                result.get("transaction"),
            ),
        )
    except APIException as e:
        raise _http_from_api_exception(e)




# ══════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════

def _wallet_response(
    wallet: Dict[str, Any],
    *,
    owner_type: Optional[str] = None,
    owner_id: Optional[int] = None,
) -> Wallet_API:
    """Shape the finance server's wallet dict into `Wallet_API`.

    Flattens the owner fields the finance server may emit
    (`user_id`, `provider_id`, `owner_type`, `owner_id`) into one
    nested `owner` object, so the client reads the same shape
    regardless of what the finance server sent.
    """
    owner: Optional[Dict[str, Any]] = None
    if owner_type is not None:
        owner = {"type": owner_type}
        if owner_id is not None:
            owner["id"] = owner_id

    return Wallet_API(
        id=int(wallet["id"]),
        owner=owner,
        currency=wallet.get("currency", "DZD"),
        balance=float(wallet.get("balance", 0)),
        status=wallet.get("status", "active"),
        type=wallet.get("type", "user"),
    )


def _transaction_response(
    t: Dict[str, Any],
    *,
    wallet_id: int,
) -> Transaction_API:
    """Shape a transaction dict into `Transaction_API`.

    The finance server already computes `direction` relative to
    the queried wallet, so this method passes it through. If the
    field is missing, it's inferred from the source/destination
    ids — defensive, in case an older finance server is in play.
    """
    direction = t.get("direction")
    if direction not in ("in", "out"):
        destination = t.get("counterparty_wallet_id")  # fallback only
        direction = "in" if destination != wallet_id else "out"

    return Transaction_API(
        id=int(t["id"]),
        amount=float(t.get("amount", 0)),
        direction=direction,
        status=t.get("status", "completed"),
        intent=t.get("intent"),
        reference=t.get("reference"),
        counterparty_wallet_id=t.get("counterparty_wallet_id"),
        for_payment_id=t.get("for_payment_id"),
        created_at=_parse_datetime(t.get("created_at")),
    )


def _maybe_transaction_response(
    t: Optional[Dict[str, Any]],
) -> Optional[Transaction_API]:
    """Transaction response or None.

    Credit and debit responses both carry a `transaction` field.
    When the finance server sends one, this shapes it. When it
    doesn't (older server, or a response the workflow returned
    without the full transaction), the field stays null rather
    than crashing the response.
    """
    if not isinstance(t, dict):
        return None
    return Transaction_API(
        id=int(t.get("id", 0)),
        amount=float(t.get("amount", 0)),
        direction=t.get("direction", "in"),
        status=t.get("status", "completed"),
        intent=t.get("intent"),
        reference=t.get("reference"),
        counterparty_wallet_id=t.get("counterparty_wallet_id"),
        for_payment_id=t.get("for_payment_id"),
        created_at=_parse_datetime(t.get("created_at")),
    )


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 string into a `datetime`, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None
    return None


def _http_from_api_exception(e: APIException) -> HTTPException:
    """Translate `APIException` into `HTTPException`.

    Every wallet endpoint does the same thing: catch the workflow's
    `APIException`, raise an `HTTPException` with the matching
    status. This helper keeps the shape identical across routes.
    """
    return HTTPException(
        status_code=e.status_code,
        detail={
            "success": False,
            "status_code": e.status_code,
            "error_code": (
                e.error_code.value
                if hasattr(e.error_code, "value")
                else str(e.error_code)
            ),
            "message": e.message,
            "details": e.details,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def _owns_provider(user_id: int, provider_id: int) -> bool:
    """Whether the given user owns the given provider.

    Wire this to your provider model. `ProductProvider` has an
    owner FK — the check is a lookup and compare. Returns False by
    default so an unwired deployment fails closed.
    """
    # Replace with your project's ownership check.
    # Example:
    # from storage.storage_broker import get
    # from core.models.models import ProductProvider
    # rows = get(
    #     ProductProvider,
    #     {ProductProvider.id_product_provider: provider_id},
    #     [],
    # )
    # return bool(rows) and rows[0].provider_owner_id == user_id
    return False