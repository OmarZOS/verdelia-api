# app/routers/action_link_router.py
"""
Action link endpoints.

Two operations:

  POST /link/create  — mint a link token for an entity and an
                       action. Called by internal services.

  POST /link/redeem  — consume a link token. Called by the
                       frontend when the user clicks a link in an
                       email, SMS, or URL.

Four actions are wired:

  * `pay`                    — pay an invoice on the finance server
  * `authorize_charge`       — authorize a card charge against an
                               invoice on the finance server
  * `accept_delivery_change` — accept a proposed delivery state
                               change
  * `receive_proposal`       — read a payload the sender embedded
                               in the token. No entity, no state
                               transition; the token *is* the
                               payload.

The workflow owns the sequencing — which service to call, when to
consume the nonce, how to handle idempotency. This router only
parses HTTP and translates exceptions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from core.exceptions.handler import APIException
from workflows.action_link_workflow import ActionLinkWorkflow

logger = logging.getLogger(__name__)


action_link_router = APIRouter()


# ── Supported actions ──────────────────────────────────────────────
#
# These four strings match the constants in
# `services/action_link_service.py`. Adding a new action means
# adding a constant there, adding a branch to the service's
# `dispatch`, and adding the entry here.
from core.models.api_models import (
    ActionType,
    CreateActionLink_API,
    CreatedActionLink_API,
    LinkEntityType,
    RedeemActionLink_API,
    RedeemedActionLink_API,
)
SUPPORTED_ACTIONS = frozenset(a.value for a in ActionType)

def get_action_link_workflow() -> ActionLinkWorkflow:
    """Construct a workflow.

    No session dependency. The workflow composes the action link
    service and the nonce service; those own their own
    persistence.
    """
    return ActionLinkWorkflow()

    


@action_link_router.post(
    "/create",
    response_model=CreatedActionLink_API,
    status_code=status.HTTP_201_CREATED,
)
async def create_action_link(
    payload: CreateActionLink_API,
    workflow: ActionLinkWorkflow = Depends(get_action_link_workflow),
):
    try:
        result = await workflow.create_link(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            action=payload.action,
            issued_to=payload.issued_to,
            ttl_hours=payload.ttl_hours,
            build_url=payload.build_url,
            base_url=payload.base_url,
            extra_claims=payload.extra_claims,
        )
        return CreatedActionLink_API(**result)
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
    response_model=RedeemedActionLink_API,
)
async def redeem_action_link(
    payload: RedeemActionLink_API,
    workflow: ActionLinkWorkflow = Depends(get_action_link_workflow),
):
    try:
        result = await workflow.redeem_link(
            token=payload.token,
            idempotency_key=payload.idempotency_key,
            notes=payload.notes,
        )
        return RedeemedActionLink_API(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Link redemption failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Link redemption failed: {str(e)}",
        )