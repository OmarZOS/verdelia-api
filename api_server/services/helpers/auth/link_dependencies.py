# ==================================================================
# Token decoding
# ==================================================================
#
# One verifier, four typed payloads. The verifier decodes the JWT,
# validates the standard claims, and — when the caller says which
# token_type it expects — returns a payload object with the fields
# that type carries. Wrong-type tokens are rejected here rather
# than at each endpoint.

from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from typing import Any, Dict, Optional

from constants import LINK_ALGORITHM, LINK_SECRET_KEY
from core.logging_config import get_logger
from services.helpers.auth.auth_dependencies import JWTBearer
from repositories.user_repository import UserRepository
from core.models.models import AppUser
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError, JWTClaimsError


logger = get_logger(__name__)
# ── Payload types ──────────────────────────────────────────────────

@dataclass(frozen=True)
class TokenPayload:
    """Base payload. Every decoded token has these fields.

    Returned by `verify_token` when `expected_type` isn't supplied.
    Callers that need the type-specific fields should either
    pass `expected_type` or dispatch on `token_type` themselves.
    """
    token_type: str
    iat: int
    exp: int
    iss: str
    raw: Dict[str, Any]   # the full decoded claims, for edge cases


@dataclass(frozen=True)
class AccessPayload(TokenPayload):
    """Decoded access token.

    Carries whatever `data` the caller passed to
    `create_access_token` — typically `app_user_id`, `username`,
    `email`, `roles`. The known fields are exposed as attributes;
    anything else is in `raw`.
    """
    app_user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[list] = None


@dataclass(frozen=True)
class RefreshPayload(TokenPayload):
    """Decoded refresh token.

    Refresh tokens are single-purpose: exchange for a new access
    token. They carry the user id and nothing else that matters.
    """
    app_user_id: int
    username: Optional[str] = None


@dataclass(frozen=True)
class OtpPayload(TokenPayload):
    """Decoded OTP token.

    `purpose` says which OTP check was passed. `destination` is the
    phone number or email the OTP was sent to, when supplied at
    creation. The consumer checks both against the operation it's
    about to perform.
    """
    app_user_id: int
    purpose: str
    destination: Optional[str] = None


@dataclass(frozen=True)
class LinkPayload(TokenPayload):
    """Decoded link token.

    `nonce` is what makes the link single-use when the caller
    stores it. `issued_to` is the user the link was generated for,
    when supplied. `extra` holds any additional claims the creator
    put in.
    """
    entity_type: str
    entity_id: int
    action: str
    nonce: str
    issued_to: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


# ── Verifier ───────────────────────────────────────────────────────

from typing import overload, Literal, Union


@overload
def verify_token(
    token: str,
    *,
    expected_type: Literal["access"],
) -> AccessPayload: ...

@overload
def verify_token(
    token: str,
    *,
    expected_type: Literal["refresh"],
) -> RefreshPayload: ...

@overload
def verify_token(
    token: str,
    *,
    expected_type: Literal["otp"],
) -> OtpPayload: ...

@overload
def verify_token(
    token: str,
    *,
    expected_type: Literal["link"],
) -> LinkPayload: ...

@overload
def verify_token(
    token: str,
    *,
    expected_type: None = None,
) -> TokenPayload: ...


def verify_token(
    token: str,
    *,
    expected_type: Optional[str] = None,
) -> TokenPayload:
    """Decode a JWT and validate its claims.

    Args:
        token: The raw JWT string.
        expected_type: Optional. When supplied, the token's
            `token_type` claim must equal this. A mismatch is a
            403 — the token is valid, it's just the wrong kind
            for this endpoint. When omitted, any token_type is
            accepted and the caller inspects the return value.

    Returns:
        A typed payload. The concrete class depends on
        `expected_type` (when supplied) or on the token's own
        `token_type` claim (when not).

    Raises:
        HTTPException(401) — the token can't be decoded: bad
            signature, malformed, expired, missing required
            claims. The client should obtain a new token.
        HTTPException(403) — the token decodes but isn't the right
            type for this call. The client has a token, it's just
            not the one this endpoint accepts.

    Every call site that knows which token type it expects should
    pass `expected_type`. The overloads give back a typed payload,
    and a type checker will catch a caller that reads a field the
    type doesn't have.
    """
    # ── Decode ─────────────────────────────────────────────────
    try:
        claims = jwt.decode(
            token,
            LINK_SECRET_KEY,
            algorithms=[LINK_ALGORITHM],
        )
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if not isinstance(claims, dict):
        # `jwt.decode` can return non-dicts when the payload
        # encoded isn't a JSON object. Reject.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
        )

    # ── Standard claims ────────────────────────────────────────
    token_type = claims.get("token_type")
    if not isinstance(token_type, str) or not token_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing token_type",
        )

    iat = claims.get("iat")
    exp = claims.get("exp")
    if not isinstance(iat, int) or not isinstance(exp, int):
        # `jose` enforces exp during decode, but a token with a
        # missing iat still parses. Reject so downstream code that
        # expects both fields can rely on them.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing iat or exp",
        )

    iss = claims.get("iss", "")

    # ── Type check ─────────────────────────────────────────────
    if expected_type is not None and token_type != expected_type:
        logger.warning(
            f"Token type mismatch: expected {expected_type!r}, "
            f"got {token_type!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"This endpoint requires a {expected_type} token"
            ),
        )

    # ── Build the typed payload ────────────────────────────────
    common = dict(
        token_type=token_type,
        iat=iat,
        exp=exp,
        iss=iss,
        raw=claims,
    )

    if token_type == "access":
        return AccessPayload(
            **common,
            app_user_id=_require_int(claims, "app_user_id"),
            username=_opt_str(claims, "username"),
            email=_opt_str(claims, "email"),
            roles=claims.get("roles"),
        )

    if token_type == "refresh":
        return RefreshPayload(
            **common,
            app_user_id=_require_int(claims, "app_user_id"),
            username=_opt_str(claims, "username"),
        )

    if token_type == "otp":
        return OtpPayload(
            **common,
            app_user_id=_require_int(claims, "app_user_id"),
            purpose=_require_str(claims, "purpose"),
            destination=_opt_str(claims, "destination"),
        )

    if token_type == "link":
        # `extra` is every claim not part of the standard or
        # link-specific set. That's what the creator put in
        # `extra_claims` at issue time.
        reserved = {
            "token_type", "iat", "exp", "iss",
            "entity_type", "entity_id", "action",
            "nonce", "issued_to",
        }
        extra = {
            k: v for k, v in claims.items()
            if k not in reserved
        }

        return LinkPayload(
            **common,
            entity_type=_require_str(claims, "entity_type"),
            entity_id=_require_int(claims, "entity_id"),
            action=_require_str(claims, "action"),
            nonce=_require_str(claims, "nonce"),
            issued_to=claims.get("issued_to"),
            extra=extra or None,
        )

    # A token_type that decodes and passes the standard checks but
    # isn't one of the four known kinds. Could be a forward-
    # compatibility case (the auth server issued a new type this
    # version of the code doesn't understand) or a forgery that
    # somehow got the signing key. Either way, reject: this
    # function only returns payloads it recognizes.
    logger.warning(
        f"Token decoded with unknown token_type {token_type!r}"
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unknown token type: {token_type}",
    )


# ── Claim helpers ──────────────────────────────────────────────────

def _require_int(claims: Dict[str, Any], name: str) -> int:
    """Return `claims[name]` as an int, or raise 401.

    A token that decodes but is missing a required claim is
    malformed for its type. Treating it as invalid (401) rather
    than forbidden (403) is correct: there's nothing the client
    can do with this token.
    """
    value = claims.get(name)
    if not isinstance(value, int):
        # Some issuers serialize ids as strings. Accept a
        # numeric string and coerce.
        if isinstance(value, str) and value.isdigit():
            return int(value)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token is missing required claim: {name}",
        )
    return value


def _require_str(claims: Dict[str, Any], name: str) -> str:
    """Return `claims[name]` as a non-empty string, or raise 401."""
    value = claims.get(name)
    if not isinstance(value, str) or not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token is missing required claim: {name}",
        )
    return value


def _opt_str(claims: Dict[str, Any], name: str) -> Optional[str]:
    """Return `claims[name]` as a string, or None."""
    value = claims.get(name)
    return value if isinstance(value, str) else None