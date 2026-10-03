# routers/app_user_router.py
"""
User router for managing user accounts, profiles, and social interactions.
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
import logging

from core.exceptions.handler import UserNotFoundException
from core.responses.user_responses import ReactionResponseModel, UserResponseModel
from core.models.api_models import AppUser_API, AppUserUpdate_API, Location_API, Person_API, ReactionBase
from core.response_models import (
    SuccessResponseModel,
    PaginatedResponseModel,
    ErrorResponseModel,
    get_crud_error_responses
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
    """Dependency to get UserService instance"""
    return UserService()


def get_social_service() -> SocialService:
    """Dependency to get SocialService instance"""
    return SocialService()


# ==================== User Endpoints ====================

@app_user_router.get(
    "/app_user",
    # response_model=SuccessResponseModel[List[UserResponseModel]],
    summary="Get all users",
    description="Retrieve all users",
    responses={
        # 200: {
        #     "description": "Users retrieved successfully",
        #     "model": SuccessResponseModel[List[UserResponseModel]]
        # },
        **get_crud_error_responses(include_404=False)
    }
)
def get_all_users(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieve all users with pagination.
    
    - **offset**: Pagination offset (query parameter)
    - **limit**: Number of records to return (query parameter, max 1000)
    """
    logger.info(f"Fetching all users (offset={offset}, limit={limit})")
    
    result = user_service.get_all_users()
    
    return result


@app_user_router.get(
    "/app_user/{user_id}",
    # response_model=SuccessResponseModel[UserResponseModel],
    summary="Get user by ID",
    description="Retrieve a user by their ID",
    responses={
        # 200: {
        #     "description": "User retrieved successfully",
        #     "model": SuccessResponseModel[UserResponseModel]
        # },
        **get_crud_error_responses(include_404=True)
    }
)
def get_user_by_id(
    user_id: int,
    full: bool = Query(True, description="Include full user details (person, preferences)"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieve a user by ID.
    
    - **user_id**: User ID to fetch (path parameter)
    - **full**: Include full user details (query parameter)
    """
    logger.info(f"Fetching user with ID: {user_id} (full={full})")
    
    result = user_service.get_user_by_id(user_id, full)
    
    return result


@app_user_router.get(
    "/person/{person_id}",
    # response_model=SuccessResponseModel,
    summary="Get person by ID",
    description="Retrieve a person by their ID",
    responses={
        # 200: {
        #     "description": "Person retrieved successfully",
        #     "model": SuccessResponseModel
        # },
        **get_crud_error_responses(include_404=True)
    }
)
def get_person_by_id(
    person_id: int,
    social_service: SocialService = Depends(get_social_service)
):
    """
    Retrieve a person by ID.
    
    - **person_id**: Person ID to fetch (path parameter)
    """
    logger.info(f"Fetching person with ID: {person_id}")
    
    result = social_service.get_person_by_id(person_id)
    
    return result


@app_user_router.post(
    "/app_user",
    status_code=status.HTTP_201_CREATED,
    # response_model=SuccessResponseModel,
    summary="Create user",
    description="Insert a new user",
    responses={
        # 201: {
        #     "description": "User created successfully",
        #     "model": SuccessResponseModel
        # },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        409: {
            "description": "Conflict - User already exists",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=False, include_409=True)
    }
)
async def insert_user_endpoint(
    user: AppUser_API,
    person: Optional[Person_API] = None,
    location: Optional[Location_API] = None,
    provider: Optional[str] = Query(None, description="OAuth provider (google, facebook, etc.)"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Insert a new user.
    
    - **user**: User details (request body)
    - **person**: Optional person details (request body)
    - **location**: Optional location details (request body)
    - **provider**: OAuth provider (query parameter)
    """
    logger.info(f"Creating new user: {user.app_user_name}")
    
    result = await user_service.create_user(user, person, location, provider)
    
    # user_id = getattr(result, 'id_app_user', None)
    
    return result


@app_user_router.delete(
    "/app_user",
    status_code=status.HTTP_200_OK,
    # response_model=SuccessResponseModel,
    summary="Delete user",
    description="Delete a user",
    responses={
        # 200: {
        #     "description": "User deleted successfully",
        #     "model": SuccessResponseModel
        # },
        400: {
            "description": "Bad Request - Cannot delete user with dependencies",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def delete_user_endpoint(
    user: AppUser_API,
    force_delete: bool = Query(False, description="Force delete even if user has dependencies"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete a user.
    
    - **user**: User details (request body)
    - **force_delete**: Force delete even if user has dependencies (query parameter)
    """
    logger.info(f"Deleting user with ID: {user.id_app_user} (force={force_delete})")
    
    result = user_service.delete_user(user)
    
    return result




@app_user_router.put(
    "/app_user/update_image_url",
    # response_model=SuccessResponseModel,
    summary="Update user image URL",
    description="Update the user image URL",
    responses={
        # 200: {
        #     "description": "Image URL updated successfully",
        #     "model": SuccessResponseModel
        # },
        **get_crud_error_responses(include_404=True)
    }
)
def update_user_image_url_endpoint(
    user: AppUser_API,
    image_url: str = Query(..., description="New image URL"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update the user image URL.
    
    - **user**: User details (request body)
    - **image_url**: New image URL (query parameter)
    """
    logger.info(f"Updating image URL for user ID: {user.id_app_user}")
    
    result = user_service.update_user_image_url(user, image_url)
    
    return SuccessResponseModel(
        success=True,
        message="Image URL updated successfully",
        data=result,
        details={
            "user_id": user.id_app_user,
            "image_url": image_url
        }
    )


@app_user_router.put(
    "/app_user",
    # response_model=SuccessResponseModel,
    summary="Update user record",
    description="Update the user record",
    responses={
        # 200: {
        #     "description": "User updated successfully",
        #     "model": SuccessResponseModel
        # },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def update_user_record_endpoint(
    user: AppUser_API,
    person_record: Person_API,
    location_record: Location_API,
    user_service: UserService = Depends(get_user_service)
):
    """
    Update the user record.
    
    - **user**: Updated user details (request body)
    - **person_record**: Updated person details (request body)
    - **location_record**: Updated location details (request body)
    """
    logger.info(f"Updating user record for ID: {user.id_app_user}")
    
    return user_service.update_user(user, person_record, location_record)


# ==================== Social/Reaction Endpoints ====================

@app_user_router.post(
    "/reaction",
    status_code=status.HTTP_201_CREATED,
    # response_model=SuccessResponseModel[ReactionResponseModel],
    summary="Add or update reaction",
    description="Insert a reaction or update an existing one",
    responses={
        # 201: {
        #     "description": "Reaction processed successfully",
        #     "model": SuccessResponseModel[ReactionResponseModel]
        # },
        400: {
            "description": "Bad Request - Invalid reaction data",
            "model": ErrorResponseModel
        },
        404: {
            "description": "Not Found - Target not found",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def reaction_endpoint(
    reaction: ReactionBase,
    social_service: SocialService = Depends(get_social_service)
):
    """
    Insert a reaction or update an existing one.
    
    - **reaction**: Reaction details (request body)
    """
    logger.info(f"Processing reaction - user:{reaction.user_id}, target:{reaction.target_id}, type:{reaction.reaction_type}")
    
    result = social_service.handle_reaction(reaction)
    
    return result
    


# ==================== Additional User Endpoints ====================

@app_user_router.get(
    "/app_user/search",
    # response_model=SuccessResponseModel[List[UserResponseModel]],
    summary="Search users",
    description="Search users by username or email",
    responses={
        # 200: {
        #     "description": "Users found successfully",
        #     "model": SuccessResponseModel[List[UserResponseModel]]
        # },
        **get_crud_error_responses(include_404=False)
    }
)
def search_users(
    query: str = Query(..., min_length=2, description="Search query (username or email)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search users by username or email.
    
    - **query**: Search query (minimum 2 characters)
    - **limit**: Maximum number of results (max 100)
    """
    logger.info(f"Searching users with query: '{query}' (limit={limit})")
    
    result = user_service.search_users(query, limit)
    
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Found {len(result) if isinstance(result, list) else 0} users matching '{query}'",
        details={
            "search_query": query,
            "limit": limit,
            "total_found": len(result) if isinstance(result, list) else 0
        }
    )


@app_user_router.get(
    "/app_user/by-email/{email}",
    # response_model=SuccessResponseModel[UserResponseModel],
    summary="Get user by email",
    description="Retrieve a user by their email address",
    responses={
        # 200: {
        #     "description": "User retrieved successfully",
        #     "model": SuccessResponseModel[UserResponseModel]
        # },
        **get_crud_error_responses(include_404=True)
    }
)
def get_user_by_email(
    email: str,
    user_service: UserService = Depends(get_user_service)
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