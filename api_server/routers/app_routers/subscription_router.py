# routers/subscription_router.py
"""
Subscription and plan router.

Handles the plan catalogue (public reads), the user's subscription
lifecycle (read status, purchase, cancel), and the usage/quota reads
that are scoped to a subscription.

Routers stay thin: parse, delegate, return. The purchase sequence and
cancellation sequence live in [SubscriptionWorkflow]. Quota reads
delegate to [UsageWorkflow] — the workflow layer is what knows how to
combine a plan's limits with a subscription's current usage.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from services.domain_limit_service import DomainLimitService
from services.helpers.domain_counters import wire_domain_counters
from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import HTTP_404_NOT_FOUND
from core.models.app_models import ResourceCode
from core.response_models import (
    ErrorResponseModel,
    get_crud_error_responses,
)

from services.subscription_service import SubscriptionService
from workflows.subscription_workflow import SubscriptionWorkflow
from workflows.usage_workflow import UsageWorkflow

logger = logging.getLogger(__name__)


subscription_router = APIRouter(
    # tags=["Subscriptions"],
    # prefix="/api/v1"
)


# ==================== Dependency Injection ====================

def get_subscription_service() -> SubscriptionService:
    return SubscriptionService()


def get_subscription_workflow() -> SubscriptionWorkflow:
    """Dependency for the subscription lifecycle endpoints.

    Constructed per-request. Holds no state between calls.
    """
    return SubscriptionWorkflow()

def get_domain_limit_service() -> DomainLimitService:
    """Construct a DomainLimitService with the domain counters
    registered.

    No session is threaded through. Each counter calls
    `storage_broker.count(...)`, which owns its own connection.
    Constructing a fresh service per request is cheap — the counters
    are just lambdas.
    """
    service = DomainLimitService()
    wire_domain_counters(service)
    return service


def get_usage_workflow(
    domain_limits: DomainLimitService = Depends(get_domain_limit_service),
) -> UsageWorkflow:
    """Construct a UsageWorkflow with the wired domain service."""
    return UsageWorkflow(domain_limits=domain_limits)

# ==================== Plan catalogue (public) ====================

@subscription_router.get(
    "/plans",
    summary="Get all plans",
    description=(
        "Retrieve every plan, optionally filtered by type and "
        "billing cycle."
    ),
    responses={
        **get_crud_error_responses(include_404=False),
    },
)
def get_plans(
    plan_type: Optional[str] = Query(
        None,
        description="Filter by 'individual' or 'organization'",
    ),
    billing_cycle: Optional[str] = Query(
        None,
        description=(
            "Filter by 'monthly', 'semestrial', 'yearly', or 'lifetime'"
        ),
    ),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    List all plans.

    Plans have no ownership — this endpoint is public and callers
    don't need to be authenticated to browse pricing. The filter
    parameters let the client render separate tabs for individual vs.
    organization plans without pulling the full catalogue.

    - **plan_type**: Optional filter, `individual` or `organization`
    - **billing_cycle**: Optional filter, one of the four cycle values
    """
    logger.info(
        f"Listing plans (plan_type={plan_type}, cycle={billing_cycle})"
    )
    return service.get_all_plans(
        plan_type=plan_type,
        billing_cycle=billing_cycle,
    )


@subscription_router.get(
    "/plans/{plan_id}",
    summary="Get plan by ID",
    description="Retrieve a single plan by its ID.",
    responses={
        **get_crud_error_responses(include_404=True),
    },
)
def get_plan_by_id(
    plan_id: int,
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Get a plan by ID.

    - **plan_id**: Plan ID to fetch
    """
    logger.info(f"Fetching plan {plan_id}")
    plan = service.get_plan_by_id(plan_id)
    if plan is None:
        raise APIException(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.PLAN_NOT_FOUND,
            details={"plan_id": plan_id},
        )
    return plan


# ==================== Subscription reads ====================

@subscription_router.get(
    "/app_user/{user_id}/subscription",
    summary="Get user's subscription",
    description="Retrieve the subscription a user currently points at.",
    responses={
        **get_crud_error_responses(include_404=True),
    },
)
def get_user_subscription(
    user_id: int,
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Get a user's current subscription.

    Null result means the user has no subscription on file — which
    is a normal state for free-tier users, not an error. The 404
    here signals "no subscription"; the client treats it as "show
    upgrade CTA" rather than as a failure.

    - **user_id**: User whose subscription to fetch
    """
    logger.info(f"Fetching subscription for user {user_id}")
    subscription = service.get_subscription_for_user(user_id)
    if subscription is None:
        raise APIException(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
            details={"user_id": user_id},
        )
    return subscription


@subscription_router.get(
    "/app_user/{user_id}/subscription/status",
    summary="Check user's subscription status",
    description=(
        "Whether the user has an active, unexpired subscription."
    ),
    responses={
        **get_crud_error_responses(include_404=False),
    },
)
def get_user_subscription_status(
    user_id: int,
    workflow: SubscriptionWorkflow = Depends(get_subscription_workflow),
):
    """
    Lightweight status check.

    Returns `active: false` rather than a 404 when the user has no
    subscription — the client polls this on app start to decide which
    features to show, and a 404 would force it to treat "no
    subscription" as an error.

    - **user_id**: User to check
    """
    logger.info(f"Checking subscription status for user {user_id}")
    return {
        "user_id": user_id,
        "active": workflow.is_subscription_active(user_id),
    }


# ==================== Subscription lifecycle ====================

@subscription_router.post(
    "/app_user/{user_id}/subscription/initiate",
    status_code=status.HTTP_201_CREATED,
    summary="Purchase a subscription",
    description=(
        "End-to-end subscription purchase: creates the invoice, the "
        "payment, confirms the payment, and returns a live "
        "subscription. No second call needed for the client."
    ),
    responses={
        201: {
            "description": "Subscription created",
        },
        400: {
            "description": "Bad Request - Plan is free (use link-free)",
            "model": ErrorResponseModel,
        },
        404: {
            "description": "Not Found - User or plan not found",
            "model": ErrorResponseModel,
        },
        409: {
            "description": "Conflict - Already subscribed to this plan",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True, include_409=True),
    },
)
async def initiate_subscription(
    user_id: int,
    plan_id: int = Query(..., description="Plan the user is buying"),
    payment_method: str = Query(
        ...,
        description=(
            "One of: cash, card, bank_transfer, mobile_money, crypto, "
            "deposit, wallet, check"
        ),
    ),
    notes: Optional[str] = Query(
        None, description="Optional notes on the payment"
    ),
    workflow: SubscriptionWorkflow = Depends(get_subscription_workflow),
):
    """
    Purchase a subscription in a single call.

    The workflow creates the invoice, creates the payment on the
    finance side, confirms it, and then finalizes the subscription —
    so the response carries a live subscription rather than a pending
    payment. The client does not need to call `finalize` afterwards.

    Free plans should not use this endpoint — call
    `POST /app_user/{user_id}/subscription/link-free` instead.

    - **user_id**: User buying the subscription
    - **plan_id**: Plan being purchased
    - **payment_method**: How the user is paying
    - **notes**: Optional payment notes
    """
    logger.info(
        f"Initiate subscription: user={user_id} plan={plan_id} "
        f"method={payment_method}"
    )
    return await workflow.initiate(
        user_id=user_id,
        plan_id=plan_id,
        payment_method=payment_method,
        notes=notes,
    )


@subscription_router.post(
    "/app_user/{user_id}/subscription/finalize",
    summary="Finalize a subscription after payment (internal)",
    description=(
        "Internal endpoint called by the finance service webhook after "
        "a payment clears. Not part of the client flow — "
        "`POST .../subscription/initiate` already finalizes "
        "synchronously. Kept for the async webhook path and for "
        "recovery pollers. Idempotent."
    ),
    responses={
        200: {
            "description": "Subscription created or already exists",
        },
        404: {
            "description": "Not Found - Payment or plan not found",
            "model": ErrorResponseModel,
        },
        409: {
            "description": "Conflict - Payment not completed",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True, include_409=True),
    },
    include_in_schema=False,
)
async def finalize_subscription(
    user_id: int,
    payment_id: int = Query(
        ..., description="Payment that cleared for this purchase"
    ),
    plan_id: int = Query(
        ..., description="Plan that the payment was for"
    ),
    workflow: SubscriptionWorkflow = Depends(get_subscription_workflow),
):
    """
    Finalize a subscription from a completed payment.

    In the current synchronous flow, `initiate` already calls this
    internally after confirming the payment, so the client never hits
    this endpoint directly. It exists for two cases:

      1. Webhook path — the finance service calls this when a payment
         clears asynchronously.
      2. Recovery path — a poller finds completed payments that never
         produced a subscription and runs them through here.

    Safe to call multiple times: if a subscription already exists for
    the payment id, returns it rather than creating a duplicate.

    Hidden from the OpenAPI schema because it's not a client-facing
    operation.

    - **user_id**: User whose subscription is being finalized
    - **payment_id**: Payment that completed
    - **plan_id**: Plan the payment was for
    """
    logger.info(
        f"Finalize subscription: user={user_id} payment={payment_id} "
        f"plan={plan_id}"
    )
    return await workflow.finalize(user_id, payment_id, plan_id)


@subscription_router.post(
    "/app_user/{user_id}/subscription/link-free",
    status_code=status.HTTP_201_CREATED,
    summary="Attach a free plan to a user",
    description=(
        "Creates a subscription for a zero-priced plan without going "
        "through the payment flow."
    ),
    responses={
        201: {
            "description": "Free subscription created",
        },
        400: {
            "description": "Bad Request - Plan is not free",
            "model": ErrorResponseModel,
        },
        404: {
            "description": "Not Found - User or plan not found",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True),
    },
)
def link_free_plan(
    user_id: int,
    plan_id: int = Query(..., description="Free plan to attach"),
    workflow: SubscriptionWorkflow = Depends(get_subscription_workflow),
):
    """
    Attach a zero-priced plan without a payment.

    Used for the default free tier and for comped plans issued by
    support. Any plan with a non-zero price rejects with 400 — the
    paid path must go through initiate/finalize.

    - **user_id**: User receiving the plan
    - **plan_id**: Free plan to attach
    """
    logger.info(f"Link free plan: user={user_id} plan={plan_id}")
    return workflow.link_free_plan(user_id, plan_id)


@subscription_router.delete(
    "/app_user/{user_id}/subscription",
    summary="Cancel a user's subscription",
    description=(
        "Unlinks the user from their subscription and zeroes their "
        "local quota. Optionally refunds the associated payment."
    ),
    responses={
        200: {
            "description": "Subscription cancelled",
        },
        404: {
            "description": "Not Found - No subscription on file",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True),
    },
)
async def cancel_subscription(
    user_id: int,
    refund_payment_id: Optional[int] = Query(
        None,
        description=(
            "Optional payment to refund as part of the cancellation. "
            "Omit to cancel without a refund."
        ),
    ),
    workflow: SubscriptionWorkflow = Depends(get_subscription_workflow),
):
    """
    Cancel a user's subscription.

    Delegates the refund to the finance service when a payment id is
    supplied, then unlinks the user and zeroes the local quota mirror.
    The subscription row itself is left in place — cancellation is a
    user-side state change, not a deletion.

    - **user_id**: User whose subscription to cancel
    - **refund_payment_id**: Optional payment to refund
    """
    logger.info(
        f"Cancel subscription: user={user_id} "
        f"refund_payment={refund_payment_id}"
    )
    return await workflow.cancel(
        user_id=user_id,
        refund_payment_id=refund_payment_id,
    )


# ==================== Usage / quota reads ====================

@subscription_router.get(
    "/app_user/{user_id}/usage",
    summary="Get current usage summary",
    description=(
        "Current counts and limits for every period-counted resource "
        "on the user's plan."
    ),
    responses={
        **get_crud_error_responses(include_404=False),
    },
)
def get_user_usage(
    user_id: int,
    workflow: UsageWorkflow = Depends(get_usage_workflow),
):
    """
    Usage summary for the account screen.

    Returns a map of resource code → { current, limit, remaining,
    allowed, kind }. A user with no subscription gets zeros for every
    resource rather than a 404 — "no plan" and "no usage" are the same
    answer from the client's perspective.

    - **user_id**: User whose usage to summarize
    """
    logger.info(f"Fetching usage summary for user {user_id}")
    return workflow.usage_summary(user_id, list(ResourceCode))


@subscription_router.get(
    "/app_user/{user_id}/usage/{resource}",
    summary="Get current usage for one resource",
    description=(
        "Current count for a single period-counted resource, plus its "
        "limit and remaining headroom."
    ),
    responses={
        **get_crud_error_responses(include_404=False),
    },
)
def get_user_usage_for_resource(
    user_id: int,
    resource: ResourceCode,
    workflow: UsageWorkflow = Depends(get_usage_workflow),
):
    """
    Usage for one resource.

    `resource` is a path parameter typed as `ResourceCode`, so an
    unknown value is a 422 by FastAPI's own validation rather than a
    lookup miss.

    - **user_id**: User whose usage to fetch
    - **resource**: One of the resource codes (e.g. `ai_credits_monthly`)
    """
    logger.info(
        f"Fetching usage for user {user_id} resource {resource.value}"
    )
    summary = workflow.usage_summary(user_id, [resource])
    return summary.get(resource.value, {
        "current": 0,
        "limit": 0,
        "remaining": 0,
        "allowed": False,
        "kind": "disabled",
    })
@subscription_router.get(
    "/app_user/{user_id}/provider/{provider_id}/usage",
    summary="Get provider-scoped usage",
    description=(
        "Current counts and limits for products and services on a "
        "single provider."
    ),
    responses={
        **get_crud_error_responses(include_404=False),
    },
)
def get_provider_usage(
    user_id: int,
    provider_id: int,
    workflow: UsageWorkflow = Depends(get_usage_workflow),
):
    """
    Usage for one provider's resources.

    Answers the question the user summary can't: "how many products
    and services does this specific provider have, and what's the
    plan's headroom?" The user summary reports `scope:
    "per_provider"` for those resources because the answer depends
    on which provider you're asking about.

    - **user_id**: User whose plan governs the limits
    - **provider_id**: Provider whose counts to fetch
    """
    logger.info(
        f"Fetching provider usage: user={user_id} "
        f"provider={provider_id}"
    )
    return workflow.provider_usage_summary(user_id, provider_id)