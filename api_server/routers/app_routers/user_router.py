# routers/app_user_router.py
"""
User router for managing user accounts, profiles, and social
interactions.

Routers stay thin: parse the request, delegate to the appropriate
layer, return the response. Coordinated multi-service operations go
through [UserWorkflow]; single-service reads and social actions go
straight to their service.

Subscription and plan endpoints live in `subscription_router.py`.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from core.exceptions.handler import UserNotFoundException
from core.response_models import (
    ErrorResponseModel,
    SuccessResponseModel,
    get_crud_error_responses,
)
from core.responses.user_responses import ReactionResponseModel
from core.models.api_models import (
    AppUser_API,
    Location_API,
    Person_API,
    ReactionBase,
)
from core.logging_config import get_logger

from services.user_service import UserService
from services.social_service import SocialService
from workflows.user_workflow import UserWorkflow

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
    deleting a user + their auth record.
    """
    return UserWorkflow()


def get_social_service() -> SocialService:
    """Dependency to get SocialService instance."""
    return SocialService()


# ==================== User reads ====================

@app_user_router.get(
    "/app_user",
    summary="Get all users",
    description="Retrieve all users",
    responses={**get_crud_error_responses(include_404=False)},
)
def get_all_users(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
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
    responses={**get_crud_error_responses(include_404=True)},
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
    responses={**get_crud_error_responses(include_404=True)},
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


@app_user_router.get(
    "/app_user/search",
    summary="Search users",
    description="Search users by username or email",
    responses={**get_crud_error_responses(include_404=False)},
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
    responses={**get_crud_error_responses(include_404=True)},
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


# ==================== User writes ====================

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


@app_user_router.put(
    "/app_user/update_image_url",
    summary="Update user image URL",
    description="Update the user image URL",
    responses={**get_crud_error_responses(include_404=True)},
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


@app_user_router.delete(
    "/app_user",
    status_code=status.HTTP_200_OK,
    summary="Delete user",
    description="Delete a user",
    responses={
        400: {
            "description": (
                "Bad Request - Cannot delete user with dependencies"
            ),
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

    Coordinates: auth record deletion followed by AppUser row
    deletion, in that order, so a failure on either side leaves the
    account in a recoverable state.

    - **user**: User details (request body)
    - **force_delete**: Force delete even if user has dependencies
      (query parameter)
    """
    logger.info(
        f"Deleting user with ID: {user.id_app_user} "
        f"(force={force_delete})"
    )
    return await workflow.delete_user(user)


# ==================== Social / reactions ====================

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