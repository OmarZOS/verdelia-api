# routers/app_routers/auth_router.py
"""
Auth router: login, tokens, OAuth, and the current-user endpoints.

Public auth endpoints (login, refresh, OAuth callbacks) stay on
[AuthService] — they don't cross service boundaries. The current-user
endpoints (change password, delete account) go through
[UserWorkflow] because they coordinate between the auth backend and
the user service.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    Depends,
    UploadFile,
    status,
)
from pydantic import BaseModel

from workflows.user_workflow import UserWorkflow
from services.helpers.auth.auth_dependencies import (
    JWTBearer,
    get_current_user,
    get_current_user_access_token,
    get_current_user_id,
    get_current_user_info,
)
from services.helpers.auth.user_dependencies import verify_user
from services.helpers.auth.auth import create_access_token, create_refresh_token
from core.exceptions.handler import AuthLoginException, OAuthException, APIException
from core.messages import *
from core.responses.auth_responses import (
    AccountDeletionConfirmation,
    AvatarUploadResponse,
    ChangePassword_API,
    ChangePasswordResponse,
    DeleteAccountResponse,
    ErrorResponseModel,
    LogoutResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
    UserProfileUpdate_API,
)
from core.models.api_models import AuthData_API
from core.exceptions.error_responses import ErrorResponse, create_error_response
from services.auth_service import AuthService
from services.oauth_config_service import OAuthConfigService
from services.user_service import UserService
from core.models.models import AppUser
from core.logging_config import get_logger

logger = get_logger(__name__)


# ==================== Router ====================

auth_router = APIRouter()


# ==================== Dependency injection ====================

def get_auth_service() -> AuthService:
    return AuthService()


def get_oauth_config() -> OAuthConfigService:
    return OAuthConfigService()


def get_user_service() -> UserService:
    return UserService()


def get_user_workflow() -> UserWorkflow:
    """Workflow dependency for endpoints that coordinate user + auth."""
    return UserWorkflow()


# ==================== Public Routes (No Auth Required) ====================

@auth_router.get(
    "/login/{provider}",
    summary="Login with OAuth provider",
    description="Redirects user to the OAuth provider's login page.",
    responses={
        302: {
            "description": "Redirect to OAuth provider",
            "headers": {
                "Location": {
                    "description": "OAuth provider authorization URL",
                    "schema": {"token_type": "string"},
                }
            },
        },
        400: {
            "description": "Bad Request - Unsupported provider",
            "model": ErrorResponseModel,
        },
        500: {
            "description": "Internal Server Error - OAuth configuration error",
            "model": ErrorResponseModel,
        },
    },
)
async def login(
    provider: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    oauth_config: OAuthConfigService = Depends(get_oauth_config),
):
    """
    Redirects user to the OAuth provider's login page.

    - **provider**: OAuth provider name (google, facebook, github)
    """
    if not oauth_config.is_supported_provider(provider):
        raise OAuthException()

    oauth_client = oauth_config.get_client(provider)
    if not oauth_client:
        raise OAuthException()

    return await auth_service.handle_oauth_login(provider, request, oauth_client)


@auth_router.get(
    "/auth/{provider}",
    summary="OAuth Callback",
    description="Handles the OAuth provider's callback and retrieves user info.",
    responses={
        302: {"description": "Redirect to frontend with user data or error"},
        400: {"description": "Bad Request - OAuth callback error", "model": ErrorResponseModel},
        401: {"description": "Unauthorized - Invalid OAuth state", "model": ErrorResponseModel},
        500: {"description": "Internal Server Error", "model": ErrorResponseModel},
    },
)
async def auth_callback(
    provider: str,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    oauth_config: OAuthConfigService = Depends(get_oauth_config),
):
    """
    Handles the OAuth provider's callback and retrieves user info.

    - **provider**: OAuth provider name (google, facebook, github)
    """
    if not oauth_config.is_supported_provider(provider):
        return auth_service.create_redirect_response(
            {}, error=f"Unsupported provider: {provider}"
        )

    oauth_client = oauth_config.get_client(provider)
    if not oauth_client:
        return auth_service.create_redirect_response(
            {},
            error=f"OAuth provider '{provider}' not properly configured",
        )

    return await auth_service.handle_oauth_callback(provider, request, oauth_client)


@auth_router.post(
    "/authentication/token",
    response_model=TokenResponse,
    summary="Login User",
    description="Authenticates the user and returns an access token.",
    responses={
        200: {"description": "Successfully authenticated", "model": TokenResponse},
        401: {"description": "Unauthorized - Invalid credentials", "model": ErrorResponseModel},
    },
)
async def login_user(
    user: AuthData_API,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticates the user and returns an access token.

    - **username**: User's username
    - **password**: User's password
    """
    try:
        auth_result = await auth_service.login_user(user)

        logger.info(f"Auth result for {user.app_user_name}: {auth_result.keys()}")

        token_data = {
            "app_user_id": auth_result.get("app_user_id"),
            "username": auth_result.get("username"),
            "email": auth_result.get("email"),
            "first_name": auth_result.get("first_name"),
            "last_name": auth_result.get("last_name"),
            "iss": "verdelia-api",
            "aud": ["verdelia-web", "verdelia-mobile"],
            "access_token": auth_result.get("access_token"),
            "refresh_token": auth_result.get("refresh_token"),
        }

        logger.info(f"Creating token for: {json.dumps(token_data)}")

        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(seconds=auth_result.get("expires_in", 3600)),
        )

        refresh_token = create_refresh_token(
            data={"app_user_id": auth_result.get("app_user_id")}
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=auth_result.get("expires_in", 3600),
            app_user_id=auth_result.get("app_user_id"),
            username=auth_result.get("username"),
            email=auth_result.get("email"),
            first_name=auth_result.get("first_name"),
            last_name=auth_result.get("last_name"),
        )

    except AuthLoginException as e:
        logger.error(f"Login failed for {user.app_user_name}: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "status_code": 401,
                "code": e.details.get("error_code", "INVALID_CREDENTIALS"),
                "message": str(e),
                "timestamp": datetime.time().isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Unexpected login error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "status_code": 500,
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@auth_router.post(
    "/authentication/refresh",
    response_model=TokenResponse,
    summary="Refresh Token",
    description="Refresh the access token using a refresh token.",
    responses={
        200: {"description": "Token refreshed successfully", "model": TokenResponse},
        401: {"description": "Unauthorized - Invalid refresh token", "model": ErrorResponseModel},
    },
)
async def refresh_token(
    refresh_token_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh the access token.
    """
    try:
        result = await auth_service.refresh_access_token(
            refresh_token_data.refresh_token
        )

        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="bearer",
            expires_in=result.get("expires_in", 3600),
            app_user_id=result.get("app_user_id"),
        )

    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "status_code": 401,
                "code": "INVALID_REFRESH_TOKEN",
                "message": "Invalid refresh token",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


# ==================== Protected Routes (Auth Required) ====================

@auth_router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Current User Profile",
    description="Get the current authenticated user's profile information.",
    responses={
        200: {"description": "User profile retrieved successfully", "model": UserProfileResponse},
        401: {"description": "Unauthorized - Invalid or missing token", "model": ErrorResponseModel},
        403: {"description": "Forbidden - Account inactive", "model": ErrorResponseModel},
    },
)
async def get_current_user_profile(
    user: AppUser = Depends(verify_user),
    user_info: Dict[str, Any] = Depends(get_current_user_info),
):
    """
    Get current authenticated user's profile.
    Requires valid JWT token.
    """
    logger.info(f"id_app_user: {user.id_app_user}")
    logger.info(f"app_user_name: {user.app_user_name}")
    logger.info(f"app_user_email: {user.app_user_email}")
    logger.info(f"app_user_preferences: {user.app_user_preferences}")
    logger.info(f"app_user_creation: {user.app_user_creation}")
    logger.info(f"app_user_image_url: {user.app_user_image_url}")

    return UserProfileResponse(
        user_id=user.id_app_user,
        username=user.app_user_name,
        email=str(user.app_user_email),
        app_user_preferences=user.app_user_preferences,
        app_user_creation=user.app_user_creation,
        user_type=user.app_user_type,
        image_url=user.app_user_image_url,
    )


@auth_router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update Current User Profile",
    description="Update the current authenticated user's profile information.",
    responses={
        200: {"description": "User profile updated successfully", "model": UserProfileResponse},
        401: {"description": "Unauthorized - Invalid or missing token", "model": ErrorResponseModel},
        422: {"description": "Validation Error", "model": ErrorResponseModel},
    },
)
async def update_current_user_profile(
    user_update: UserProfileUpdate_API,
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """
    Update current user's profile.
    Requires valid JWT token.
    """
    try:
        updated_user = await user_service.update_user_profile(
            user_id=user_id,
            update_data=user_update,
        )

        return UserProfileResponse(
            user_id=updated_user.id_app_user,
            username=updated_user.app_user_name,
            email=updated_user.app_user_email,
            first_name=updated_user.person.person_first_name,
            last_name=updated_user.person.person_last_name,
            user_type=updated_user.app_user_type,
            created_at=updated_user.app_user_created_at,
            image_url=updated_user.app_user_image_url,
        )

    except Exception as e:
        logger.error(f"Update user profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}",
        )


@auth_router.post(
    "/me/change-password",
    response_model=ChangePasswordResponse,
    summary="Change Password",
    description="Change the current user's password.",
    responses={
        200: {"description": "Password changed successfully", "model": ChangePasswordResponse},
        401: {"description": "Unauthorized - Invalid or missing token", "model": ErrorResponseModel},
        400: {"description": "Bad Request - Invalid password", "model": ErrorResponseModel},
    },
)
async def change_password(
    password_data: ChangePassword_API,
    user_info: Dict[str, Any] = Depends(get_current_user_info),
    workflow: UserWorkflow = Depends(get_user_workflow),
):
    """
    Change current user's password.

    Coordinates: the workflow looks up the user (to get the username
    the auth backend expects), delegates the password change, and
    refreshes the local hash. The router only supplies the identity
    from the JWT and the new password.

    Requires valid JWT token.
    """
    try:
        await workflow.change_password(
            user_id=user_info["user_id"],
            new_password=password_data.new_password,
            token=user_info.get("access_token"),
        )

        return ChangePasswordResponse(
            success=True,
            message="Password changed successfully",
            user_id=user_info["user_id"],
            changed_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )


@auth_router.post(
    "/me/upload-avatar",
    response_model=AvatarUploadResponse,
    summary="Upload Avatar",
    description="Upload a new avatar image for the current user.",
    responses={
        200: {"description": "Avatar uploaded successfully", "model": AvatarUploadResponse},
        401: {"description": "Unauthorized - Invalid or missing token", "model": ErrorResponseModel},
        422: {"description": "Validation Error", "model": ErrorResponseModel},
    },
)
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """
    Upload a new avatar image.
    Requires valid JWT token.
    """
    try:
        avatar_url = await user_service.upload_avatar(
            user_id=user_id,
            file=file,
        )

        return AvatarUploadResponse(
            success=True,
            message="Avatar uploaded successfully",
            avatar_url=avatar_url,
        )

    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}",
        )


@auth_router.delete(
    "/me/delete-account",
    response_model=DeleteAccountResponse,
    summary="Delete Account",
    description="Delete the current user's account.",
    responses={
        200: {"description": "Account deleted successfully", "model": DeleteAccountResponse},
        401: {"description": "Unauthorized - Invalid or missing token", "model": ErrorResponseModel},
        400: {"description": "Bad Request", "model": ErrorResponseModel},
    },
)
async def delete_account(
    confirmation_data: AccountDeletionConfirmation,
    user_id: int = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
    workflow: UserWorkflow = Depends(get_user_workflow),
):
    """
    Delete the current user's account.

    Coordinates: password verification (auth service), then the
    workflow deletes the auth record followed by the user row. Ordering
    means a failed auth delete leaves the account intact so the user
    can retry.

    Requires valid JWT token.
    """
    try:
        # Verify password before proceeding — the workflow shouldn't
        # delete anything if the caller can't prove ownership.
        result = await auth_service.verify_password(
            user_id=user_id,
            current_password=confirmation_data.password,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password verification failed",
            )

        await workflow.delete_user(user_id, delete_auth=True)

        return DeleteAccountResponse(
            success=True,
            message="Account deleted successfully",
            user_id=user_id,
            deleted_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}",
        )


@auth_router.get(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout User",
    description="Logs out the user by clearing the session.",
    responses={
        200: {"description": "Successfully logged out", "model": LogoutResponse},
        401: {"description": "Unauthorized - No active session", "model": ErrorResponseModel},
        500: {"description": "Internal Server Error", "model": ErrorResponseModel},
    },
)
async def logout(
    request: Request,
    payload: Dict[str, Any] = Depends(JWTBearer()),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logs out the user by clearing the session.
    Requires valid JWT token.
    """
    result = auth_service.logout_user(request)
    return LogoutResponse(
        success=result["success"],
        message=result["message"],
        timestamp=datetime.now(),
    )


# ==================== Admin Routes (Admin Only) ====================

@auth_router.get(
    "/admin/users",
    response_model=List[UserProfileResponse],
    summary="Get All Users",
    description="Get all users (Admin only).",
    responses={
        200: {"description": "Users retrieved successfully", "model": List[UserProfileResponse]},
        401: {"description": "Unauthorized - Invalid or missing token", "model": ErrorResponseModel},
        403: {"description": "Forbidden - Admin only", "model": ErrorResponseModel},
    },
)
async def get_all_users(
    payload: Dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get all users. Admin only.
    Requires valid JWT token and admin privileges.
    """
    if payload.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    users = await user_service.get_all_users()
    return [
        UserProfileResponse(
            user_id=user.id_app_user,
            username=user.app_user_name,
            email=user.app_user_email,
            first_name=user.person.person_first_name,
            last_name=user.person.person_last_name,
            user_type=user.app_user_type,
            created_at=user.app_user_created_at,
            image_url=user.app_user_image_url,
        )
        for user in users
    ]