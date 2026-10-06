# app/routers/action_link_router.py
"""
Action link endpoints.

Two operations:

  POST /link/create  — mint a link token for an entity and an
                       action. Returns a URL that the caller
                       emails, SMSes, or embeds.

  POST /link/redeem  — consume a link token. The token names the
                       entity and the action; the endpoint
                       verifies the token, ensures the entity is
                       in a state where the action makes sense,
                       then performs the action.

Four actions are wired:

  * `pay`                    — pay an invoice
  * `authorize_charge`       — authorize a card charge against an
                               invoice, pending 2FA
  * `accept_payment_request` — accept a peer payment request
  * `accept_delivery_change` — accept a proposed delivery state
                               change

All four use `create_link_token` / `verify_token` from
`app/auth.py`. Nonces are stored in `opaque_link_token` (or
whatever table backs single-use links in your schema) so a link
can only be redeemed once.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth import create_link_token, verify_token, LinkPayload
from core.database import session_scope
from core.exceptions.handler import APIException
from services.link_nonce_service import LinkNonceService
from services.action_link_service import ActionLinkService

logger = logging.getLogger(__name__)


action_link_router = APIRouter(tags=["Action Links"])


# ==================== Enums as constants ====================

# Supported actions. Adding a new one means adding a branch to
# `ActionLinkService.dispatch` below — the router itself doesn't
# need to change.
ACTION_PAY = "pay"
ACTION_AUTHORIZE_CHARGE = "authorize_charge"
ACTION_ACCEPT_PAYMENT_REQUEST = "accept_payment_request"
ACTION_ACCEPT_DELIVERY_CHANGE = "accept_delivery_change"

SUPPORTED_ACTIONS = frozenset({
    ACTION_PAY,
    ACTION_AUTHORIZE_CHARGE,
    ACTION_ACCEPT_PAYMENT_REQUEST,
    ACTION_ACCEPT_DELIVERY_CHANGE,
})


# ==================== Request models ====================

class CreateLinkRequest(BaseModel):
    """Ask the API to mint a link.

    The caller says what the link is for and which entity it acts
    on. The API returns a token and, if requested, a full URL the
    caller can hand to the recipient.
    """
    entity_type: str = Field(
        ...,
        description=(
            "What the link acts on — 'invoice', 'payment_request', "
            "'delivery'."
        ),
        min_length=1,
        max_length=32,
    )
    entity_id: int = Field(
        ...,
        description="Id of the entity in its own table.",
    )
    action: str = Field(
        ...,
        description=(
            "What the link does on redemption. One of: "
            + ", ".join(sorted(SUPPORTED_ACTIONS))
        ),
    )
    issued_to: Optional[int] = Field(
        None,
        description=(
            "Optional user id the link is issued to. On redemption "
            "the API can require the same user to be logged in."
        ),
    )
    ttl_hours: Optional[int] = Field(
        None,
        gt=0,
        le=24 * 30,
        description=(
            "Override the default lifetime. Defaults to the "
            "LINK_TOKEN_EXPIRE_HOURS constant."
        ),
    )
    build_url: bool = Field(
        True,
        description=(
            "When true, the response includes a full URL the "
            "caller can send. When false, only the raw token is "
            "returned and the caller composes the URL itself."
        ),
    )
    base_url: Optional[str] = Field(
        None,
        description=(
            "Base URL for the built URL. Required when build_url "
            "is true. Ignored otherwise."
        ),
    )
    extra_claims: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Additional claims to embed in the token. Useful for "
            "context the redeemer needs — a display name, a "
            "preferred language. Cannot override reserved claims."
        ),
    )

    @field_validator("action")
    @classmethod
    def _valid_action(cls, v: str) -> str:
        if v not in SUPPORTED_ACTIONS:
            raise ValueError(
                f"action must be one of {sorted(SUPPORTED_ACTIONS)}"
            )
        return v

    @field_validator("base_url")
    @classmethod
    def _base_url_required(cls, v, info):
        # If the caller asked for a URL, they must supply the base.
        # This runs after the other fields are validated.
        wants_url = info.data.get("build_url", True)
        if wants_url and not v:
            raise ValueError(
                "base_url is required when build_url is true"
            )
        return v


class RedeemLinkRequest(BaseModel):
    """Present a link token for redemption.

    The token names the entity and the action; the endpoint trusts
    the token for that. Everything else in this body is optional
    context — idempotency keys, caller-supplied notes, the reason
    a delivery is being accepted.
    """
    token: str = Field(
        ...,
        min_length=8,
        description="The link token from the URL.",
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=64,
        description=(
            "Optional key. Two redeems with the same key and the "
            "same token return the same result rather than "
            "performing the action twice."
        ),
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Free-form notes recorded on the action.",
    )


# ==================== Response models ====================

class CreateLinkResponse(BaseModel):
    token: str
    url: Optional[str] = None
    entity_type: str
    entity_id: int
    action: str
    expires_at: datetime


class RedeemLinkResponse(BaseModel):
    success: bool
    action: str
    entity_type: str
    entity_id: int
    result: Dict[str, Any]
    already_redeemed: bool = False


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    error_code: Optional[str] = None
    errors: Optional[list[ErrorDetail]] = None
    timestamp: str
    path: Optional[str] = None


# ==================== Dependencies ====================



def get_link_nonce_service(
    db: Session = Depends(get_db),
) -> LinkNonceService:
    """Service that tracks issued link nonces.

    The token carries a nonce. This service is what makes that
    nonce single-use — it stores issued nonces and marks them
    consumed on redemption. If your system has a different
    single-use mechanism, swap it in here.
    """
    return LinkNonceService(db)


def get_action_link_service(
    db: Session = Depends(get_db),
    nonce_service: LinkNonceService = Depends(get_link_nonce_service),
) -> ActionLinkService:
    """Service that executes the actions a link authorizes."""
    return ActionLinkService(db, nonce_service)


# ==================== Endpoints ====================

@action_link_router.post(
    "/create",
    response_model=CreateLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mint a link token",
    responses={
        201: {"description": "Link created"},
        400: {"description": "Bad request", "model": ErrorResponse},
        404: {
            "description": "Entity not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Entity is not in a state that accepts "
                           "this action",
            "model": ErrorResponse,
        },
        500: {"description": "Internal error", "model": ErrorResponse},
    },
)
async def create_action_link(
    payload: CreateLinkRequest,
    service: ActionLinkService = Depends(get_action_link_service),
):
    """Mint a link token for an entity and an action.

    The caller is a trusted service (an internal admin action, a
    billing job, a delivery orchestrator). This endpoint is not
    exposed to end users — the API server calls it when it needs
    to issue a link.

    The endpoint verifies that the entity exists and is in a state
    where the action makes sense *now*. A "pay" link for an already
    paid invoice is a 409, not a 201 with a link that will fail
    later.
    """
    try:
        if payload.ttl_hours is not None:
            from datetime import timedelta
            expires_delta = timedelta(hours=payload.ttl_hours)
        else:
            expires_delta = None

        # Pre-check the entity. The service loads the entity and
        # raises 404 or 409 if it can't take this action.
        service.assert_action_viable(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            action=payload.action,
        )

        token = create_link_token(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            action=payload.action,
            issued_to=payload.issued_to,
            expires_delta=expires_delta,
            extra_claims=payload.extra_claims,
        )

        # Record the nonce so redemption can be single-use.
        claims = verify_token(token, expected_type="link")
        service.register_nonce(
            nonce=claims.nonce,
            entity_type=claims.entity_type,
            entity_id=claims.entity_id,
            action=claims.action,
            issued_to=claims.issued_to,
            expires_at=datetime.fromtimestamp(
                claims.exp, tz=timezone.utc,
            ),
        )

        url = None
        if payload.build_url:
            base = payload.base_url.rstrip("/")
            url = f"{base}?token={token}"

        logger.info(
            f"Link created: entity={payload.entity_type}:"
            f"{payload.entity_id} action={payload.action!r} "
            f"issued_to={payload.issued_to}"
        )

        return CreateLinkResponse(
            token=token,
            url=url,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            action=payload.action,
            expires_at=datetime.fromtimestamp(
                claims.exp, tz=timezone.utc,
            ),
        )

    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Link creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Link creation failed: {str(e)}",
        )


@action_link_router.post(
    "/redeem",
    response_model=RedeemLinkResponse,
    summary="Redeem a link token",
    responses={
        200: {"description": "Action performed"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {
            "description": "Invalid or expired token",
            "model": ErrorResponse,
        },
        403: {
            "description": "Token is not for this operation",
            "model": ErrorResponse,
        },
        404: {
            "description": "Entity not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Entity is not in a state that accepts "
                           "this action",
            "model": ErrorResponse,
        },
        410: {
            "description": "Link already used",
            "model": ErrorResponse,
        },
        500: {"description": "Internal error", "model": ErrorResponse},
    },
)
async def redeem_action_link(
    payload: RedeemLinkRequest,
    service: ActionLinkService = Depends(get_action_link_service),
):
    """Redeem a link token and perform the action it authorizes.

    The endpoint:

      1. Verifies the token. A malformed or expired token is a 401;
         a token of the wrong type is a 403.
      2. Checks the nonce. A consumed nonce is a 410; a missing
         nonce is a 404.
      3. Loads the entity and confirms it can still take the
         action. An already-paid invoice is a 409.
      4. Dispatches to the action handler. The handler does the
         work and returns a result dict.
      5. Marks the nonce consumed. If the handler succeeded, the
         link is spent. If it failed, the nonce is left untouched
         so the client can retry.

    The order matters: the nonce is consumed only after the action
    succeeds. A request that fails partway through doesn't burn
    the link.
    """
    try:
        # 1. Verify the token.
        claims: LinkPayload = verify_token(
            payload.token, expected_type="link",
        )

        # 2. Check the nonce.
        service.assert_nonce_valid(claims.nonce)

        # 3. Assert the entity can still take the action.
        service.assert_action_viable(
            entity_type=claims.entity_type,
            entity_id=claims.entity_id,
            action=claims.action,
        )

        # 4. Dispatch.
        result = service.dispatch(
            claims=claims,
            idempotency_key=payload.idempotency_key,
            notes=payload.notes,
        )

        # 5. Consume the nonce now that the action succeeded.
        service.consume_nonce(claims.nonce)

        logger.info(
            f"Link redeemed: entity={claims.entity_type}:"
            f"{claims.entity_id} action={claims.action!r} "
            f"nonce={claims.nonce[:8]}..."
        )

        return RedeemLinkResponse(
            success=True,
            action=claims.action,
            entity_type=claims.entity_type,
            entity_id=claims.entity_id,
            result=result,
            already_redeemed=False,
        )

    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link redemption failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Link redemption failed: {str(e)}",
        )