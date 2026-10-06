# app/auth.py
from asyncio.log import logger
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Any, Dict, Optional
from core.messages import *
from fastapi import Depends,  status
from sqlalchemy.orm import Session
from constants import ACCESS_TOKEN_EXPIRE_MINUTES,  REFRESH_TOKEN_EXPIRE_DAYS ,API_ALGORITHM,API_SECRET_KEY,LINK_ALGORITHM,LINK_SECRET_KEY




def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token from client data.
    
    Args:
        data: Data to encode in token (from auth server)
        expires_delta: Optional custom expiration
    
    Returns:
        JWT token string
    """
    import time
    from datetime import datetime, timedelta, timezone
    
    to_encode = data.copy()
    
    # Get current time as integer timestamp
    now = int(time.time())
    
    # Set expiration as integer timestamp
    if expires_delta:
        expire = now + int(expires_delta.total_seconds())
    else:
        expire = now + int(timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds())
    
    # Add standard JWT claims as integers
    to_encode.update({"exp": expire})
    to_encode.update({"iat": now})
    
    # Optional: Add issuer if not present
    if "iss" not in to_encode:
        to_encode.update({"iss": "verdelia-auth-server"})
    
    # Log for debugging
    logger.debug(f"Creating token with exp: {expire} (type: {type(expire)})")
    logger.debug(f"Creating token with iat: {now} (type: {type(now)})")
    
    # Encode JWT - no need to convert datetimes
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm=API_ALGORITHM)
    
    logger.debug(f"Access token created for user {data.get('app_user_id')}")
    return encoded_jwt

def convert_datetimes(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(item) for item in obj]
    else:
        return obj

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token from client data.
    """
    to_encode = data.copy()
    to_encode.update({"token_type": "refresh"})
    
    if expires_delta:
        expire = datetime.time() + expires_delta
    else:
        expire = datetime.time() + timedelta(days=int(REFRESH_TOKEN_EXPIRE_DAYS))
    
    to_encode.update({"exp": expire})
    to_encode.update({"iat": datetime.time()})
    
    to_encode = convert_datetimes(to_encode)
    
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm=API_ALGORITHM)
    
    logger.debug(f"Refresh token created for user {data.get('app_user_id')}")
    return encoded_jwt





# ==================================================================
# Link tokens
# ==================================================================
#
# Three token types, one per purpose:
#
#   access   — authenticates a session. Handled above.
#   otp      — proves a user passed an OTP check for a specific
#              purpose (phone verification, password reset, 2FA).
#   link     — carries a one-shot nonce for a URL sent out of band
#              (email confirmation, invoice payment link, magic
#              login). Meant to be consumed once and then
#              invalidated server-side.
#
# All three share the same signing key and algorithm as access
# tokens. The `token_type` claim distinguishes them so a verifier
# can reject a link token presented where an access token is
# expected, and vice versa.
#
# Lifetimes come from `constants.py`:
#   OTP_TOKEN_EXPIRE_MINUTES   — short, matches the OTP's own TTL
#   LINK_TOKEN_EXPIRE_HOURS    — the default for emailed links

import secrets
import time

from constants import (
    OTP_TOKEN_EXPIRE_MINUTES,
    LINK_TOKEN_EXPIRE_HOURS,
)


# ── Internal helpers ───────────────────────────────────────────────

def _now_ts() -> int:
    """Current time as a Unix timestamp (integer seconds)."""
    return int(time.time())


def _exp_ts(delta: timedelta) -> int:
    """Unix timestamp for `delta` from now."""
    return _now_ts() + int(delta.total_seconds())


# ── OTP token ──────────────────────────────────────────────────────

def create_otp_token(
    user_id: int,
    purpose: str,
    *,
    destination: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT that proves a user passed an OTP check.

    Args:
        user_id: The user who proved the OTP.
        purpose: Which check was passed. Conventional values:
            `"phone_verify"`, `"email_verify"`, `"password_reset"`,
            `"login_2fa"`. The consumer verifies this against the
            operation it's about to perform — an OTP token for
            phone verification cannot be used to reset a password.
        destination: Optional — the phone number or email address
            the OTP was sent to. When supplied, the consumer can
            check that the OTP was proven against the same
            destination the operation now touches.
        expires_delta: Optional override. Defaults to
            `OTP_TOKEN_EXPIRE_MINUTES` minutes.

    Returns:
        JWT token string.

    Claims:
        `app_user_id`, `token_type="otp"`, `purpose`, `destination`
        (when supplied), `iss`, `iat`, `exp`.

    The lifetime should be short — minutes, not hours. The token
    exists only to bridge the moment between OTP entry and the
    operation it authorizes. A long-lived OTP token is a security
    problem: it proves something that should have already expired.
    """
    if not purpose:
        raise ValueError("create_otp_token requires a purpose")

    now = _now_ts()
    if expires_delta is not None:
        exp = _exp_ts(expires_delta)
    else:
        exp = _exp_ts(
            timedelta(minutes=int(OTP_TOKEN_EXPIRE_MINUTES))
        )

    claims: Dict[str, Any] = {
        "app_user_id": user_id,
        "token_type": "otp",
        "purpose": purpose,
        "iss": "verdelia-api-server",
        "iat": now,
        "exp": exp,
    }
    if destination is not None:
        claims["destination"] = destination

    encoded = jwt.encode(claims, LINK_SECRET_KEY, algorithm=LINK_ALGORITHM)
    logger.debug(
        f"OTP token created for user {user_id} purpose={purpose!r}"
    )
    return encoded


# ── Link token ─────────────────────────────────────────────────────

def create_link_token(
    entity_type: str,
    entity_id: int,
    action: str,
    *,
    issued_to: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a JWT for a link sent out of band.

    Args:
        entity_type: What the link is about — `"invoice"`,
            `"delivery"`, `"user"`, `"subscription"`. The consumer
            matches this against the entity it's about to act on.
        entity_id: The specific row's id.
        action: What the link does — `"pay"`, `"confirm"`,
            `"reset"`, `"view"`, `"download"`. The consumer checks
            this against the endpoint the link points at, so a
            "view" link can't be replayed against a "cancel"
            endpoint.
        issued_to: Optional — the user id the link was generated
            for. Useful when the consumer wants to require that
            the same user is logged in when the link is used.
        expires_delta: Optional override. Defaults to
            `LINK_TOKEN_EXPIRE_HOURS` hours.
        extra_claims: Optional dict merged into the token's claims.
            Use this to carry context the consumer needs — an
            invoice number for display, an email address the link
            was sent to. Do not put secrets here; the token is
            base64-encoded, not encrypted.

    Returns:
        JWT token string.

    Claims:
        `entity_type`, `entity_id`, `action`, `nonce`,
        `token_type="link"`, `issued_to` (when supplied), `iss`,
        `iat`, `exp`, plus anything in `extra_claims`.

    The `nonce` is a random URL-safe string, unique per issued
    token. If the link must be single-use, the caller stores the
    nonce server-side when the link is issued and deletes it when
    the link is redeemed. The function only puts the nonce in the
    token; storage is the caller's concern.

    Lifetimes are measured in hours or days. A password-reset link
    typically lives an hour; an invoice payment link may live a
    week. Pass `expires_delta` when the default doesn't fit.
    """
    if not entity_type:
        raise ValueError("create_link_token requires entity_type")
    if not action:
        raise ValueError("create_link_token requires action")

    now = _now_ts()
    if expires_delta is not None:
        exp = _exp_ts(expires_delta)
    else:
        exp = _exp_ts(
            timedelta(hours=int(LINK_TOKEN_EXPIRE_HOURS))
        )

    claims: Dict[str, Any] = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "nonce": secrets.token_urlsafe(24),
        "token_type": "link",
        "iss": "verdelia-api-server",
        "iat": now,
        "exp": exp,
    }
    if issued_to is not None:
        claims["issued_to"] = issued_to
    if extra_claims:
        # Caller-supplied claims don't override the ones above.
        # The reserved fields (token_type, iat, exp, nonce, iss)
        # are set by this function and shouldn't be shadows.
        reserved = {
            "token_type", "iat", "exp", "nonce", "iss",
            "entity_type", "entity_id", "action",
        }
        for k, v in extra_claims.items():
            if k in reserved:
                raise ValueError(
                    f"extra_claims cannot override reserved claim "
                    f"{k!r}"
                )
            claims[k] = v

    encoded = jwt.encode(claims, LINK_SECRET_KEY, algorithm=LINK_ALGORITHM)
    logger.debug(
        f"Link token created for {entity_type}:{entity_id} "
        f"action={action!r}"
    )
    return encoded


# ── Opaque link token ──────────────────────────────────────────────
#
# The above `create_link_token` produces a JWT: the payload is
# visible to anyone who has the token (base64-decoded), it's just
# not forgeable. For some link kinds that's fine — "click to
# confirm your email" doesn't need to hide the user id inside it.
#
# For other link kinds the payload itself is sensitive. A magic
# login link, for example, shouldn't advertise the user id and
# email in its URL fragment. The opaque variant inverts the model:
# the URL carries a random lookup key, and the *server* holds the
# payload in a table keyed by that random value.

def create_opaque_link_token(
    *,
    length: int = 32,
) -> str:
    """Generate a random, URL-safe opaque link token.

    Returns:
        A random string suitable for use as a URL path segment or
        query parameter. Not a JWT. Contains no encoded data —
        whoever holds the token learns nothing except that they
        hold a token.

    The caller stores the mapping `token -> payload` (or
    `token -> entity, action, expiry`) in the database. When the
    link is opened, the server looks up the token, retrieves the
    payload, and either performs the action or redirects
    appropriately. The token itself carries no claims.

    `length` is the number of random bytes before URL-safe
    encoding. 32 bytes → 43 characters. That's ~256 bits of
    entropy — a lookup key rather than a capability, but far
    beyond brute force.

    Use this variant when:
      * The payload is sensitive (a user id paired with an email,
        an amount, a security question answer).
      * The link must be revocable at any time (the caller deletes
        the row).
      * The link is issued frequently enough that a server-side
        table is cheap (magic links, one-time downloads).

    Use `create_link_token` (JWT) when:
      * The payload is safe to expose in the URL (entity id,
        action name).
      * Server-side storage is inconvenient (stateless backends,
        high issue rate, ephemeral infrastructure).
      * Revocation isn't required — the link simply expires when
        its `exp` claim passes.
    """
    if length < 16:
        raise ValueError(
            "length must be at least 16 bytes to provide "
            "meaningful entropy"
        )
    return secrets.token_urlsafe(length)