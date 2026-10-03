# routers/business_routers/delivery_router.py
"""
Delivery router — transport layer only.

Every route does three things and no more:

  1. Validate request shape (query params, body presence).
  2. Call exactly one method on DeliveryWorkflow.
  3. Translate domain exceptions into HTTP responses.

No reads against DeliveryService, no state checks, no policy
consultation, no `Delivery_API` construction. Those all live on the
workflow.
"""

from fastapi import APIRouter, Depends, Query, Body, status, HTTPException
from typing import Optional, Any, Dict
import logging

from core.models.api_models import Delivery_API
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.delivery_exceptions import (
    DeliveryNotFoundException,
    DeliveryNotEditableException,
    DeliveryNotArchivableException,
    DeliveryUpdateFailedException,
    DeliveryStatusInvalidException,
)
from workflows.delivery_workflow import DeliveryWorkflow

from core.logging_config import get_logger

logger = get_logger(__name__)


delivery_router = APIRouter()


# ============================================================================
# Dependency provider
# ============================================================================

def get_delivery_workflow() -> DeliveryWorkflow:
    try:
        from services.order_workflow import OrderWorkflow
        order_wf = OrderWorkflow()
    except Exception:
        order_wf = None
    return DeliveryWorkflow(order_workflow=order_wf)


TARGET_STATUSES = {
    "processing", "confirmed", "shipped", "in_transit",
    "out_for_delivery", "delivered",
    "failed", "cancelled", "returned", "refunded",
}

SIGNAL_FIELDS = (
    "delivery_confirmed",
    "in_transit_acknowledged",
    "proof_captured",
    "failure_reported",
    "return_confirmed",
    "refund_completed",
)


# ============================================================================
# Exception → HTTP translation
# ============================================================================

def _http_from_transition_error(
    action: str, e: DeliveryUpdateFailedException
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "transition_not_allowed",
            "action": action,
            "reason": str(e),
        },
    )


def _extract_signals(body: Optional[Delivery_API]) -> Dict[str, Any]:
    """Pick the non-None signal fields off the body for the policy."""
    if body is None:
        return {}
    out: Dict[str, Any] = {}
    for name in SIGNAL_FIELDS:
        value = getattr(body, name, None)
        if value is not None:
            out[name] = value
    return out


def _run_transition(
    delivery_id: int,
    action_label: str,
    workflow: DeliveryWorkflow,
    target: str,
    body: Optional[Delivery_API] = None,
) -> dict:
    """
    One call, one read, one write. The workflow patches the row in
    memory, decides, and persists in a single pass.
    """
    try:
        return workflow.transition(
            delivery_id,
            target,
            body=body,
            **_extract_signals(body),
        )
    except DeliveryNotFoundException:
        raise
    except DeliveryUpdateFailedException as e:
        raise _http_from_transition_error(action_label, e)


# ============================================================================
# READ
# ============================================================================

@delivery_router.get(
    "",
    summary="List deliveries",
    description=(
        "List deliveries filtered by provider, source, or status. "
        "At least one filter is required."
    ),
    responses={
        200: {"description": "Deliveries retrieved successfully"},
        **get_crud_error_responses(include_404=False),
    },
)
def list_deliveries(
    provider_id: int = Query(0, description="Filter by provider"),
    source_type: Optional[str] = Query(
        None, description="'placed_order' or 'cart'"
    ),
    source_id: int = Query(0, description="Filter by source ID"),
    delivery_status: Optional[str] = Query(
        None, alias="status", description="Filter by lifecycle status"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    if not any([provider_id, source_id, delivery_status]):
        raise DeliveryStatusInvalidException(
            requested_status="<none>",
            allowed_statuses=sorted(TARGET_STATUSES),
        )

    if delivery_status:
        normalized = delivery_status.lower()
        if normalized not in TARGET_STATUSES:
            raise DeliveryStatusInvalidException(
                requested_status=delivery_status,
                allowed_statuses=sorted(TARGET_STATUSES),
            )
    else:
        normalized = None

    return workflow.list_deliveries(
        provider_id=provider_id,
        source_type=source_type,
        source_id=source_id,
        status=normalized,
        offset=offset,
        limit=limit,
    )


@delivery_router.get(
    "/{delivery_id}",
    summary="Get a delivery",
    responses={
        200: {"description": "Delivery retrieved successfully"},
        **get_crud_error_responses(include_404=True),
    },
)
def get_delivery(
    delivery_id: int,
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return workflow.get_delivery(delivery_id, eager=True)


@delivery_router.get(
    "/{delivery_id}/next-states",
    summary="Which states can this delivery move to?",
    responses={
        200: {"description": "Next states returned"},
        **get_crud_error_responses(include_404=True),
    },
)
def get_delivery_next_states(
    delivery_id: int,
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return workflow.next_states(delivery_id)


# ============================================================================
# METADATA-ONLY WRITE
# ============================================================================

@delivery_router.post(
    "/{delivery_id}/details",
    summary="Update delivery details (metadata only)",
    responses={
        200: {"description": "Delivery details updated"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def update_delivery_details(
    delivery_id: int,
    body: Delivery_API = Body(...),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    try:
        return workflow.update_details(delivery_id, body)
    except DeliveryNotFoundException:
        raise
    except DeliveryNotEditableException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "not_editable",
                "current_status": e.current_status,
                "message": (
                    f"Delivery details can no longer be edited once the "
                    f"delivery is {e.current_status}."
                ),
            },
        )


# ============================================================================
# OPS — lifecycle transitions
# ============================================================================

@delivery_router.post(
    "/{delivery_id}/accept",
    summary="Accept a delivery for handling",
    responses={
        200: {"description": "Delivery accepted"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def accept_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "accept", workflow,
        target="processing", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/confirm",
    summary="Confirm the delivery is packed and ready",
    responses={
        200: {"description": "Delivery confirmed"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def confirm_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "confirm", workflow,
        target="confirmed", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/ship",
    summary="Ship the delivery",
    responses={
        200: {"description": "Delivery shipped"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def ship_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "ship", workflow,
        target="shipped", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/in-transit",
    summary="Mark the delivery in transit",
    responses={
        200: {"description": "Delivery in transit"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def mark_in_transit(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "in_transit", workflow,
        target="in_transit", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/out-for-delivery",
    summary="Mark the delivery out for delivery",
    responses={
        200: {"description": "Delivery out for delivery"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def mark_out_for_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "out_for_delivery", workflow,
        target="out_for_delivery", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/deliver",
    summary="Mark the delivery delivered",
    responses={
        200: {"description": "Delivery delivered"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def deliver_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "deliver", workflow,
        target="delivered", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/cancel",
    summary="Cancel the delivery",
    responses={
        200: {"description": "Delivery cancelled"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def cancel_delivery(
    delivery_id: int,
    reason: Optional[str] = Query(None, description="Free-text reason"),
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    result = _run_transition(
        delivery_id, "cancel", workflow,
        target="cancelled", body=body,
    )
    if reason:
        result["reason"] = reason
    return result


@delivery_router.post(
    "/{delivery_id}/fail",
    summary="Report the delivery as failed",
    responses={
        200: {"description": "Delivery failed"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def fail_delivery(
    delivery_id: int,
    reason: Optional[str] = Query(None, description="Failure reason"),
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    result = _run_transition(
        delivery_id, "fail", workflow,
        target="failed", body=body,
    )
    if reason:
        result["reason"] = reason
    return result


@delivery_router.post(
    "/{delivery_id}/return",
    summary="Mark the delivery returned",
    responses={
        200: {"description": "Delivery returned"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def return_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "return", workflow,
        target="returned", body=body,
    )


@delivery_router.post(
    "/{delivery_id}/refund",
    summary="Refund the delivery",
    responses={
        200: {"description": "Delivery refunded"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def refund_delivery(
    delivery_id: int,
    body: Optional[Delivery_API] = Body(None),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return _run_transition(
        delivery_id, "refund", workflow,
        target="refunded", body=body,
    )


# ============================================================================
# OPS — non-state attributes
# ============================================================================

@delivery_router.post(
    "/{delivery_id}/tracking-pings",
    summary="Record a tracking ping",
    responses={
        200: {"description": "Tracking recorded"},
        404: {"model": ErrorResponseModel},
    },
)
def record_tracking_ping(
    delivery_id: int,
    current_address_id: int = Query(...),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return workflow.update_tracking(delivery_id, current_address_id)


@delivery_router.post(
    "/{delivery_id}/reroute",
    summary="Re-route the delivery",
    responses={
        200: {"description": "Delivery re-routed"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def reroute_delivery(
    delivery_id: int,
    address_id: int = Query(...),
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    return workflow.update_address(delivery_id, address_id)


@delivery_router.post(
    "/{delivery_id}/archive",
    summary="Archive a delivery",
    responses={
        200: {"description": "Delivery archived"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def archive_delivery(
    delivery_id: int,
    workflow: DeliveryWorkflow = Depends(get_delivery_workflow),
):
    try:
        return workflow.delete_delivery(delivery_id, force_delete=False)
    except DeliveryNotFoundException:
        raise
    except DeliveryNotArchivableException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "not_terminal",
                "current_status": e.current_status,
                "message": (
                    "Only terminal deliveries can be archived. "
                    "Finish or cancel the delivery first."
                ),
            },
        )