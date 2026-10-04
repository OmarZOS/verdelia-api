# routers/app_user_router.py
"""
User router for managing user accounts, profiles, and social interactions.

Routers stay thin: parse the request, delegate to the appropriate
layer, return the response. Coordinated multi-service operations go
through [UserWorkflow]; single-service reads and social actions go
straight to their service.
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
import logging

from core.messages.error_codes import ErrorCode
from core.messages.http_status import HTTP_404_NOT_FOUND
from services.subscription_service import SubscriptionService
from workflows.user_workflow import UserWorkflow
from core.exceptions.handler import APIException, UserNotFoundException
from core.responses.user_responses import ReactionResponseModel, UserResponseModel
from core.models.api_models import (
    AppUser_API,
    AppUserUpdate_API,
    Location_API,
    Person_API,
    ReactionBase,
)
from core.response_models import (
    SuccessResponseModel,
    PaginatedResponseModel,
    ErrorResponseModel,
    get_crud_error_responses,
)
from services.user_service import UserService
from services.social_service import SocialService

from core.logging_config import get_logger

logger = get_logger(__name__)


app_user_router = APIRouter(
    # tags=["Users"],
    # prefix="/api/v1"
)


# ==================== Dependency Injection ====================

def get_user_service() -> UserService:
    """Dependency to get UserService instance."""
    return UserService()


def get_user_workflow() -> UserWorkflow:
    """Dependency to get UserWorkflow instance.

    Used for operations that touch more than one service — creating a
    user + their auth record, updating user + person + location,
    deleting a user + their auth record, and the subscription purchase
    flow.
    """
    return UserWorkflow()


def get_social_service() -> SocialService:
    """Dependency to get SocialService instance."""
    return SocialService()


def get_subscription_service() -> SubscriptionService:
    """Dependency to get SubscriptionService instance."""
    return SubscriptionService()


# ==================== User Endpoints ====================

@app_user_router.get(
    "/app_user",
    summary="Get all users",
    description="Retrieve all users",
    responses={
        **get_crud_error_responses(include_404=False)
    }
)
def get_all_users(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    user_service: UserService = Depends(get_user_service),
):
    """
    Retrieve all users with pagination.

    - **offset**: Pagination offset (query parameter)
    - **limit**: Number of records to return (query parameter, max 1000)
    """
    logger.info(f"Fetching all users (offset={offset}, limit={limit})")
    return user_service.get_all_users()


@app_user_router.get(
    "/app_user/{user_id}",
    summary="Get user by ID",
    description="Retrieve a user by their ID",
    responses={
        **get_crud_error_responses(include_404=True)
    }
)
def get_user_by_id(
    user_id: int,
    full: bool = Query(
        True, description="Include full user details (person, preferences)"
    ),
    user_service: UserService = Depends(get_user_service),
):
    """
    Retrieve a user by ID.

    - **user_id**: User ID to fetch (path parameter)
    - **full**: Include full user details (query parameter)
    """
    logger.info(f"Fetching user with ID: {user_id} (full={full})")
    return user_service.get_user_by_id(user_id, full)


@app_user_router.get(
    "/person/{person_id}",
    summary="Get person by ID",
    description="Retrieve a person by their ID",
    responses={
        **get_crud_error_responses(include_404=True)
    }
)
def get_person_by_id(
    person_id: int,
    social_service: SocialService = Depends(get_social_service),
):
    """
    Retrieve a person by ID.

    - **person_id**: Person ID to fetch (path parameter)
    """
    logger.info(f"Fetching person with ID: {person_id}")
    return social_service.get_person_by_id(person_id)


@app_user_router.post(
    "/app_user",
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Insert a new user",
    responses={
        201: {"description": "User created successfully"},
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel,
        },
        409: {
            "description": "Conflict - User already exists",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=False, include_409=True),
    },
)
async def insert_user_endpoint(
    user: AppUser_API,
    person: Optional[Person_API] = None,
    location: Optional[Location_API] = None,
    provider: Optional[str] = Query(
        None, description="OAuth provider (google, facebook, etc.)"
    ),
    workflow: UserWorkflow = Depends(get_user_workflow),
):
    """
    Insert a new user.

    Coordinates: uniqueness check, AppUser persistence, person +
    location attach, auth registration with rollback on failure. All
    of that lives in [UserWorkflow.create_user].

    - **user**: User details (request body)
    - **person**: Optional person details (request body)
    - **location**: Optional location details (request body)
    - **provider**: OAuth provider (query parameter)
    """
    logger.info(f"Creating new user: {user.app_user_name}")
    return await workflow.create_user(user, person, location, provider)


@app_user_router.delete(
    "/app_user",
    status_code=status.HTTP_200_OK,
    summary="Delete user",
    description="Delete a user",
    responses={
        400: {
            "description": "Bad Request - Cannot delete user with dependencies",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True),
    },
)
async def delete_user_endpoint(
    user: AppUser_API,
    force_delete: bool = Query(
        False, description="Force delete even if user has dependencies"
    ),
    workflow: UserWorkflow = Depends(get_user_workflow),
):
    """
    Delete a user.

    Coordinates: auth record deletion followed by AppUser row deletion,
    in that order, so a failure on either side leaves the account in a
    recoverable state.

    - **user**: User details (request body)
    - **force_delete**: Force delete even if user has dependencies
      (query parameter)
    """
    logger.info(
        f"Deleting user with ID: {user.id_app_user} (force={force_delete})"
    )
    return await workflow.delete_user(user)


@app_user_router.put(
    "/app_user/update_image_url",
    summary="Update user image URL",
    description="Update the user image URL",
    responses={
        **get_crud_error_responses(include_404=True)
    }
)
def update_user_image_url_endpoint(
    user: AppUser_API,
    image_url: str = Query(..., description="New image URL"),
    workflow: UserWorkflow = Depends(get_user_workflow),
):
    """
    Update the user image URL.

    Single-service operation, but routed through the workflow so the
    fetch-then-update sequence lives in one place rather than being
    duplicated between router and service.

    - **user**: User details (request body)
    - **image_url**: New image URL (query parameter)
    """
    logger.info(f"Updating image URL for user ID: {user.id_app_user}")
    result = workflow.update_user_image(user.id_app_user, image_url)
    return SuccessResponseModel(
        success=True,
        message="Image URL updated successfully",
        data=result,
        details={
            "user_id": user.id_app_user,
            "image_url": image_url,
        },
    )


@app_user_router.put(
    "/app_user",
    summary="Update user record",
    description="Update the user record",
    responses={
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True),
    },
)
def update_user_record_endpoint(
    user: AppUser_API,
    person_record: Person_API,
    location_record: Location_API,
    workflow: UserWorkflow = Depends(get_user_workflow),
):
    """
    Update the user record.

    Coordinates: person + location refresh/insert first, then the
    AppUser row points at the resulting person. Ordering means a failed
    person write leaves the user row untouched.

    - **user**: Updated user details (request body)
    - **person_record**: Updated person details (request body)
    - **location_record**: Updated location details (request body)
    """
    logger.info(f"Updating user record for ID: {user.id_app_user}")
    return workflow.update_user(user, person_record, location_record)


# ==================== Social/Reaction Endpoints ====================

@app_user_router.post(
    "/reaction",
    status_code=status.HTTP_201_CREATED,
    summary="Add or update reaction",
    description="Insert a reaction or update an existing one",
    responses={
        400: {
            "description": "Bad Request - Invalid reaction data",
            "model": ErrorResponseModel,
        },
        404: {
            "description": "Not Found - Target not found",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=True),
    },
)
def reaction_endpoint(
    reaction: ReactionBase,
    social_service: SocialService = Depends(get_social_service),
):
    """
    Insert a reaction or update an existing one.

    - **reaction**: Reaction details (request body)
    """
    logger.info(
        f"Processing reaction - user:{reaction.user_id}, "
        f"target:{reaction.target_id}, type:{reaction.reaction_type}"
    )
    return social_service.handle_reaction(reaction)


# ==================== Additional User Endpoints ====================

@app_user_router.get(
    "/app_user/search",
    summary="Search users",
    description="Search users by username or email",
    responses={
        **get_crud_error_responses(include_404=False)
    }
)
def search_users(
    query: str = Query(
        ..., min_length=2, description="Search query (username or email)"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of results"
    ),
    user_service: UserService = Depends(get_user_service),
):
    """
    Search users by username or email.

    - **query**: Search query (minimum 2 characters)
    - **limit**: Maximum number of results (max 100)
    """
    logger.info(f"Searching users with query: '{query}' (limit={limit})")
    result = user_service.search_users(query, limit)

    count = len(result) if isinstance(result, list) else 0
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Found {count} users matching '{query}'",
        details={
            "search_query": query,
            "limit": limit,
            "total_found": count,
        },
    )


@app_user_router.get(
    "/app_user/by-email/{email}",
    summary="Get user by email",
    description="Retrieve a user by their email address",
    responses={
        **get_crud_error_responses(include_404=True)
    }
)
def get_user_by_email(
    email: str,
    user_service: UserService = Depends(get_user_service),
):
    """
    Get user by email.

    - **email**: User email address (path parameter)
    """
    logger.info(f"Fetching user with email: {email}")
    result = user_service.get_user_by_email(email)

    if not result:
        raise UserNotFoundException(username=email)

    return result


# ==================== Plan Endpoints ====================

@app_user_router.get(
    "/plans",
    summary="Get all plans",
    description="Retrieve every plan, optionally filtered by type and billing cycle.",
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
        description="Filter by 'monthly', 'semestrial', 'yearly', or 'lifetime'",
    ),
    service: SubscriptionService = Depends(get_subscription_service),
):
    """
    List all plans.

    Plans have no ownership — this endpoint is public and callers don't
    need to be authenticated to browse pricing. The filter parameters
    let the client render separate tabs for individual vs. organization
    plans without pulling the full catalogue.

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


@app_user_router.get(
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


# ==================== Subscription Endpoints ====================

@app_user_router.get(
    "/app_user/{user_id}/subscription",
    summary="Get user's subscription",
    description="Retrieve the subscription a user currently points at.",
    responses={
        **get_crud_error_responses(include_404=True),
    },
)
def get_user_subscription(
    user_id: int,
    subscription_service: SubscriptionService = Depends(get_subscription_service),
):
    """
    Get a user's current subscription.

    Null result means the user has no subscription on file — which is
    a normal state for free-tier users, not an error. The 404 here
    signals "no subscription", the client treats it as "show upgrade
    CTA" rather than as a failure.

    - **user_id**: User whose subscription to fetch
    """
    logger.info(f"Fetching subscription for user {user_id}")
    subscription = subscription_service.get_subscription_for_user(user_id)
    if subscription is None:
        raise APIException(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
            details={"user_id": user_id},
        )
    return subscription


@app_user_router.get(
    "/app_user/{user_id}/subscription/status",
    summary="Check user's subscription status",
    description="Whether the user has an active, unexpired subscription.",
    responses={
        **get_crud_error_responses(include_404=False),
    },
)
def get_user_subscription_status(
    user_id: int,
    workflow: UserWorkflow = Depends(get_user_workflow),
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


@app_user_router.post(
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
    workflow: UserWorkflow = Depends(get_user_workflow),
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
    return await workflow.initiate_subscription(
        user_id=user_id,
        plan_id=plan_id,
        payment_method=payment_method,
        notes=notes,
    )


@app_user_router.post(
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
    workflow: UserWorkflow = Depends(get_user_workflow),
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
    """
    logger.info(
        f"Finalize subscription: user={user_id} payment={payment_id}"
    )
    return await workflow.finalize_subscription(user_id, payment_id)


@app_user_router.post(
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
    workflow: UserWorkflow = Depends(get_user_workflow),
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


@app_user_router.delete(
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
    workflow: UserWorkflow = Depends(get_user_workflow),
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
    return await workflow.cancel_subscription(
        user_id=user_id,
        refund_payment_id=refund_payment_id,
    )