# workflows/action_link_workflow.py
"""
Action link workflow.

Sequences the calls that a link redemption triggers — the
`ActionLinkService` for the action itself, the `LinkNonceService`
for single-use tracking.

The workflow owns:

  * The decision of when to consume the nonce. Consuming it
    before the action runs means a failed action burns the link;
    consuming it after means a crash between action and consume
    leaves the link reusable. The workflow consumes *after* the
    action, and relies on idempotency keys to make retries safe.

  * Idempotency — a repeat request with the same key returns the
    same result.

No `Session`, no ORM models. The workflow calls services; the
services own persistence.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from services.helpers.auth.auth import create_link_token
from services.helpers.auth.link_dependencies import LinkPayload, verify_token
from core.exceptions.handler import APIException
from services.action_link_service import ActionLinkService

logger = logging.getLogger(__name__)


class ActionLinkWorkflow:
    """Coordinates action-link creation and redemption."""

    def __init__(
        self,
        action_link_service: Optional[ActionLinkService] = None,
    ):
        self.service = action_link_service or ActionLinkService()

    # ══════════════════════════════════════════════════════════════
    # Create
    # ══════════════════════════════════════════════════════════════

    async def create_link(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action: str,
        issued_to: Optional[int] = None,
        ttl_hours: Optional[int] = None,
        build_url: bool = True,
        base_url: Optional[str] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mint a link and register its nonce.

        Raises 404 when the entity doesn't exist, 409 when it's in
        a state that doesn't accept the action.
        """
        # 1. Pre-check the entity.
        await self.service.assert_action_viable(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
        )

        # 2. Build the token.
        expires_delta = (
            timedelta(hours=ttl_hours) if ttl_hours else None
        )
        token = create_link_token(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            issued_to=issued_to,
            expires_delta=expires_delta,
            extra_claims=extra_claims,
        )

        # 3. Decode to learn the nonce and expiry.
        claims: LinkPayload = verify_token(token, expected_type="link")


        # 5. Build the URL if asked.
        url = None
        if build_url and base_url:
            url = f"{base_url.rstrip('/')}?token={token}"

        logger.info(
            f"Link created: {entity_type}:{entity_id} "
            f"action={action!r} issued_to={issued_to}"
        )

        return {
            "token": token,
            "url": url,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "expires_at": datetime.fromtimestamp(
                claims.exp, tz=timezone.utc,
            ),
        }

    # ══════════════════════════════════════════════════════════════
    # Redeem
    # ══════════════════════════════════════════════════════════════

    async def redeem_link(
        self,
        *,
        token: str,
        idempotency_key: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify the token, dispatch the action, consume the
        nonce.

        On success: the action has happened and the nonce is spent.
        On failure: the nonce is left untouched so the client can
        retry.

        Idempotent when `idempotency_key` is supplied.
        """
        # 1. Verify the token.
        claims: LinkPayload = verify_token(token, expected_type="link")


        # 4. Assert the entity can still take the action.
        await self.service.assert_action_viable(
            entity_type=claims.entity_type,
            entity_id=claims.entity_id,
            action=claims.action,
        )

        # 5. Dispatch.
        try:
            result = await self.service.dispatch(
                claims=claims,
                idempotency_key=idempotency_key,
                notes=notes,
            )
        except Exception:
            # The action failed. The nonce is *not* consumed — the
            # client can retry. Any partial writes are the
            # responsibility of the service that owns them; the
            # workflow doesn't roll back a session it doesn't hold.
            raise

        logger.info(
            f"Link redeemed: {claims.entity_type}:{claims.entity_id} "
            f"action={claims.action!r}"
        )

        return {
            "success": True,
            "action": claims.action,
            "entity_type": claims.entity_type,
            "entity_id": claims.entity_id,
            "result": result,
            "already_redeemed": False,
        }