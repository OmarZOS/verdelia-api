# routers/reaction_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from core.logging_config import get_logger
from core.messages.http_status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from core.models.api_models import ReactionBase, ReactionStatistics, ReactionBulkRequest, ReactionBulkResponse
from core.exceptions.handler import APIException
from core.messages import *
from core.response_models import SuccessResponseModel, ErrorResponseModel, get_crud_error_responses
from services.reaction_service import ReactionService
from constants import ReactionType

from core.logging_config import get_logger

logger = get_logger(__name__)


reaction_router = APIRouter()

def get_reaction_service() -> ReactionService:
    return ReactionService()


@reaction_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Add or update reaction",
    description="Insert a reaction or update an existing one",
    responses={
        # 201: {
        #     "description": "Reaction processed successfully",
        #     "model": SuccessResponseModel
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
def handle_reaction(
    reaction: ReactionBase,
    reaction_service: ReactionService = Depends(get_reaction_service)
):
    """
    Create or update a reaction.
    
    - **reaction**: Reaction details (request body)
    """
    logger.info(f"Processing reaction - user:{reaction.user_id}, target:{reaction.target_id}, type:{reaction.reaction_type}")
    
    try:
        result = reaction_service.handle_reaction(reaction)
        
        return result
    except APIException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error handling reaction: {e}")
        raise APIException(
            status=HTTP_500_INTERNAL_SERVER_ERROR,
            code="REACTION_PROCESSING_ERROR",
            details=str(e)
        )


@reaction_router.get(
    "/user/{user_id}/target/{target_type}/{target_id}",
    summary="Get user reaction on target",
    description="Get a user's reaction on a specific target",
    responses={
        # 200: {
        #     "description": "Reaction retrieved successfully",
        #     "model": SuccessResponseModel
        # },
        400: {
            "description": "Bad Request - Invalid reaction type",
            "model": ErrorResponseModel
        },
        404: {
            "description": "Not Found - Reaction not found",
            "model": ErrorResponseModel
        }
    }
)
def get_user_reaction(
    user_id: int,
    target_type: str,
    target_id: int,
    reaction_service: ReactionService = Depends(get_reaction_service)
):
    """
    Get a user's reaction on a specific target.
    
    - **user_id**: User ID (path parameter)
    - **target_type**: Type of target (product, recipe, provider, comment)
    - **target_id**: Target ID (path parameter)
    """
    try:
        reaction_type = ReactionType(target_type)
    except ValueError:
        raise APIException(
            status=HTTP_400_BAD_REQUEST,
            code="INVALID_REACTION_TYPE",
            details=f"Invalid reaction type: {target_type}"
        )
    
    reaction = reaction_service.get_user_reaction_on_target(
        user_id, target_id, reaction_type
    )
    
    if not reaction:
        raise APIException(
            status=HTTP_404_NOT_FOUND,
            code="REACTION_NOT_FOUND",
            details=f"Reaction not found for user {user_id} on target {target_id}"
        )
    
    return reaction


@reaction_router.delete(
    "/user/{user_id}/target/{target_type}/{target_id}",
    summary="Delete user reaction",
    description="Delete a user's reaction on a target",
    responses={
        200: {
            "description": "Reaction deleted successfully",
            "model": SuccessResponseModel
        },
        400: {
            "description": "Bad Request - Invalid reaction type",
            "model": ErrorResponseModel
        },
        404: {
            "description": "Not Found - Reaction not found",
            "model": ErrorResponseModel
        }
    }
)
def delete_user_reaction(
    user_id: int,
    target_type: str,
    target_id: int,
    reaction_service: ReactionService = Depends(get_reaction_service)
):
    """
    Delete a user's reaction on a target.
    
    - **user_id**: User ID (path parameter)
    - **target_type**: Type of target (product, recipe, provider, comment)
    - **target_id**: Target ID (path parameter)
    """
    try:
        reaction_type = ReactionType(target_type)
    except ValueError:
        raise APIException(
            status=HTTP_400_BAD_REQUEST,
            code="INVALID_REACTION_TYPE",
            details=f"Invalid reaction type: {target_type}"
        )
    
    success = reaction_service.delete_user_reaction(user_id, target_id, reaction_type)
    
    if not success:
        raise APIException(
            status=HTTP_404_NOT_FOUND,
            code="REACTION_NOT_FOUND",
            details=f"Reaction not found for user {user_id} on target {target_id}"
        )
    
    return SuccessResponseModel(
        success=True,
        message="Reaction deleted successfully",
        details={
            "user_id": user_id,
            "target_id": target_id,
            "reaction_type": target_type
        }
    )


@reaction_router.get(
    "/user/{user_id}",
    summary="Get all user reactions",
    description="Get all reactions by a user",
    responses={
        # 200: {
        #     "description": "Reactions retrieved successfully",
        #     "model": SuccessResponseModel
        # },
        404: {
            "description": "User not found",
            "model": ErrorResponseModel
        }
    }
)
def get_user_reactions(
    user_id: int,
    reaction_type: Optional[str] = None,
    reaction_service: ReactionService = Depends(get_reaction_service)
):
    """
    Get all reactions by a user.
    
    - **user_id**: User ID (path parameter)
    - **reaction_type**: Filter by reaction type (query parameter)
    """
    try:
        reaction_type_enum = None
        if reaction_type:
            reaction_type_enum = ReactionType(reaction_type)
    except ValueError:
        raise APIException(
            status=HTTP_400_BAD_REQUEST,
            code="INVALID_REACTION_TYPE",
            details=f"Invalid reaction type: {reaction_type}"
        )
    
    result = reaction_service.get_reactions_by_user(user_id, reaction_type_enum)
    
    return result


@reaction_router.get(
    "/summary/{target_type}/{target_id}",
    summary="Get reaction summary",
    description="Get summary of reactions for a target",
    responses={
        # 200: {
        #     "description": "Reaction summary retrieved successfully",
        #     "model": SuccessResponseModel[ReactionStatistics]
        # },
        400: {
            "description": "Bad Request - Invalid target type",
            "model": ErrorResponseModel
        },
        404: {
            "description": "Not Found - Target not found",
            "model": ErrorResponseModel
        }
    }
)
def get_reaction_summary(
    target_type: str,
    target_id: int,
    reaction_service: ReactionService = Depends(get_reaction_service)
):
    """
    Get summary of reactions for a target.
    
    - **target_type**: Type of target (product, recipe, provider, comment)
    - **target_id**: Target ID (path parameter)
    """
    try:
        reaction_type = ReactionType(target_type)
    except ValueError:
        raise APIException(
            status=HTTP_400_BAD_REQUEST,
            code="INVALID_TARGET_TYPE",
            details=f"Invalid target type: {target_type}"
        )
    
    summary = reaction_service.get_reaction_summary(reaction_type, target_id)
    
    return summary


@reaction_router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add/update reactions",
    description="Add or update multiple reactions at once",
    responses={
        201: {
            "description": "Reactions processed successfully",
            "model": SuccessResponseModel[ReactionBulkResponse]
        },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def handle_bulk_reactions(
    request: ReactionBulkRequest,
    reaction_service: ReactionService = Depends(get_reaction_service)
):
    """
    Add or update multiple reactions at once.
    
    - **reactions**: List of reaction details (request body)
    """
    logger.info(f"Processing {len(request.reactions)} reactions")
    
    results = []
    errors = []
    
    for reaction in request.reactions:
        try:
            result = reaction_service.handle_reaction(reaction)
            results.append({
                "user_id": reaction.user_id,
                "target_id": reaction.target_id,
                "status": result['status']
            })
        except Exception as e:
            errors.append({
                "user_id": reaction.user_id,
                "target_id": reaction.target_id,
                "error": str(e)
            })
    
    return SuccessResponseModel(
        success=len(errors) == 0,
        message=f"Processed {len(results)} reactions successfully, {len(errors)} failed",
        data=ReactionBulkResponse(
            success=len(errors) == 0,
            processed_count=len(results),
            failed_count=len(errors),
            errors=errors if errors else None
        ),
        details={
            "total": len(request.reactions),
            "processed": len(results),
            "failed": len(errors)
        }
    )