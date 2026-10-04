# services/auth_service.py

import json
import logging
import urllib
import secrets
import string
import httpx
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from fastapi import Request
from fastapi.responses import RedirectResponse

from core.messages.error_codes import ErrorCode
from core.messages.http_status import HTTP_417_EXPECTATION_FAILED
from features.auth_manager import AuthManager
from repositories.user_repository import UserRepository
from core.models.api_models import AppUser_API, AuthData_API
from core.exceptions.handler import APIException, AuthLoginException, OAuthException, OAuthProviderNotSupportedException
from core.messages import *
from constants import *
from features.auth_client import AuthClient

# Import jose exceptions correctly
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError, JWTClaimsError

from core.logging_config import get_logger

logger = get_logger(__name__)



class AuthService:
    """Service for authentication and OAuth operations"""

    user_repo = UserRepository()
    
    # Token refresh constants
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

    @staticmethod
    def get_supported_providers():
        """Get list of supported OAuth providers."""
        return ["google", "facebook", "instagram"]
    
    def __init__(self):
        self.auth_client = AuthClient()
        self.auth_manager = AuthManager()  # Uncomment when needed
    
    @staticmethod
    def generate_random_password(length: int = 32) -> str:
        """Generate a strong random password for OAuth users."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def create_redirect_response(data: Dict[str, Any], error: Optional[str] = None) -> RedirectResponse:
        """Create a redirect response with encoded data or error."""
        if error:
            encoded_data = urllib.parse.quote(error)
            deep_link = f"verdelia://auth/callback?error={encoded_data}"
        else:
            json_data = json.dumps(data, default=str)
            encoded_data = urllib.parse.quote(json_data)
            deep_link = f"verdelia://auth/callback?data={encoded_data}"
        
        return RedirectResponse(url=deep_link)
    
    # ==================== Token Generation ====================
    
    def _parse_timestamp(self, value: Union[int, float, str, None]) -> Optional[int]:
        """
        Parse timestamp from various formats.
        
        Supports:
        - Integer (Unix timestamp)
        - Float (Unix timestamp)
        - String (ISO format: '2026-06-21T19:44:27.086226')
        - String (numeric: '1737467123')
        """
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)
        
        if isinstance(value, str):
            # Try to parse as integer first (numeric string)
            try:
                return int(value)
            except ValueError:
                pass
            
            # Try to parse as ISO datetime string
            try:
                if value.endswith('Z'):
                    value = value.replace('Z', '+00:00')
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return int(dt.timestamp())
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _normalize_claims(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize claims to expected formats.
        Converts string timestamps to integers.
        """
        # Normalize iat
        if "iat" in payload:
            iat_value = self._parse_timestamp(payload["iat"])
            if iat_value is not None:
                payload["iat"] = iat_value
            else:
                logger.warning(f"Removing invalid iat claim: {payload.get('iat')}")
                del payload["iat"]
        
        # Normalize exp
        if "exp" in payload:
            exp_value = self._parse_timestamp(payload["exp"])
            if exp_value is not None:
                payload["exp"] = exp_value
            else:
                logger.warning(f"Removing invalid exp claim: {payload.get('exp')}")
                del payload["exp"]
        
        # Normalize nbf
        if "nbf" in payload:
            nbf_value = self._parse_timestamp(payload["nbf"])
            if nbf_value is not None:
                payload["nbf"] = nbf_value
            else:
                del payload["nbf"]
        
        return payload
    
    def generate_access_token(self, user_id: int, username: str, email: Optional[str] = None) -> str:
        """
        Generate a new access token.
        
        Args:
            user_id: User ID
            username: Username
            email: User email (optional)
            
        Returns:
            JWT access token
        """
        from constants import AUTH_SECRET_KEY, AUTH_ALGORITHM
        
        now = int(datetime.now(timezone.utc).timestamp())
        expire = now + (self.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        payload = {
            "app_user_id": user_id,
            "username": username,
            "token_type": "access",
            "iat": now,
            "exp": expire,
            "iss": "verdelia-api"
        }
        
        if email:
            payload["email"] = email
        
        access_token = jwt.encode(payload, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
        logger.debug(f"Access token generated for user {username} (iat: {now}, exp: {expire})")
        return access_token
    
    def generate_refresh_token(self, user_id: int, username: str) -> str:
        """
        Generate a refresh token.
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            JWT refresh token
        """
        from constants import AUTH_SECRET_KEY, AUTH_ALGORITHM
        
        now = int(datetime.now(timezone.utc).timestamp())
        expire = now + (self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)  # 30 days
        
        payload = {
            "app_user_id": user_id,
            "username": username,
            "token_type": "refresh",
            "iat": now,
            "exp": expire,
            "iss": "verdelia-api"
        }
        
        refresh_token = jwt.encode(payload, AUTH_SECRET_KEY, algorithm=AUTH_ALGORITHM)
        logger.debug(f"Refresh token generated for user {username} (iat: {now}, exp: {expire})")
        return refresh_token
    
    def generate_token_pair(self, user_id: int, username: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate both access and refresh tokens.
        
        Args:
            user_id: User ID
            username: Username
            email: User email (optional)
            
        Returns:
            Dict containing both tokens
        """
        access_token = self.generate_access_token(user_id, username, email)
        refresh_token = self.generate_refresh_token(user_id, username)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token": refresh_token,
            "refresh_token_expires_in": self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            "app_user_id": user_id,
            "username": username,
            "email": email
        }
    
    # ==================== Token Validation ====================
    
    def decode_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Decode and validate a refresh token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Decoded token payload
            
        Raises:
            APIException: If token is invalid or expired
        """
        from constants import AUTH_SECRET_KEY, AUTH_ALGORITHM
        
        try:
            # First try to decode with validation
            try:
                payload = jwt.decode(
                    refresh_token,
                    AUTH_SECRET_KEY,
                    algorithms=[AUTH_ALGORITHM],
                    options={
                        "verify_signature": True,
                        "verify_exp": False,  # We'll check manually
                        "verify_iat": False,  # Disable iat validation
                        "verify_nbf": False,  # Disable nbf validation
                        "verify_aud": False,
                        "verify_iss": False,
                    }
                )

                logger.info(f"Found this {json.dumps(payload)}")

            except JWTError as e:
                # Try to decode without validation to get the payload
                logger.warning(f"Token validation failed: {e}, attempting to decode without validation")
                try:
                    payload = jwt.decode(
                        refresh_token,
                        AUTH_SECRET_KEY,
                        algorithms=[AUTH_ALGORITHM],
                        options={
                            "verify_signature": False,
                            "verify_exp": False,
                            "verify_iat": False,
                            "verify_nbf": False,
                            "verify_aud": False,
                            "verify_iss": False,
                        }
                    )
                    logger.warning("Token decoded without validation")
                except Exception as e2:
                    logger.error(f"Failed to decode token even without validation: {e2}")
                    raise APIException(
                        status_code=401,
                        error_code="INVALID_TOKEN_FORMAT",
                        message=f"Invalid token format: {str(e2)}"
                    )
            
            # Normalize claims (convert string timestamps to integers)
            payload = self._normalize_claims(payload)
            
            # Verify it's a refresh token
            if payload.get("token_type") != "refresh":
                raise APIException(
                    status_code=401,
                    error_code="INVALID_TOKEN_TYPE",
                    message="Invalid token type",
                    details={"expected": "refresh", "received": payload.get("token_type")}
                )
            
            # Check if expired manually
            exp = payload.get("exp")
            if exp:
                try:
                    exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    
                    # Allow 5 seconds clock skew
                    clock_skew = 5
                    if exp_datetime < now_utc:
                        if (now_utc - exp_datetime).total_seconds() <= clock_skew:
                            logger.debug(f"Token expired but within clock skew ({clock_skew}s)")
                        else:
                            logger.warning(f"Token expired at {exp_datetime} (now: {now_utc})")
                            raise APIException(
                                status_code=401,
                                error_code="REFRESH_TOKEN_EXPIRED",
                                message="Refresh token has expired",
                                details={"expired_at": exp_datetime.isoformat()}
                            )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid exp claim: {exp} - {e}")
                    raise APIException(
                        status_code=401,
                        error_code="INVALID_TOKEN_EXPIRATION",
                        message="Invalid token expiration"
                    )
            
            # Check required fields
            if "app_user_id" not in payload:
                raise APIException(
                    status_code=401,
                    error_code="INVALID_TOKEN",
                    message="Invalid refresh token: missing user ID"
                )
            
            # if "username" not in payload:
            #     raise APIException(
            #         status_code=401,
            #         error_code="INVALID_TOKEN",
            #         message="Invalid refresh token: missing username"
            #     )
            
            logger.debug(f"Refresh token validated for user ID {payload.get('app_user_id')}")
            return payload
            
        except ExpiredSignatureError:
            raise APIException(
                status_code=401,
                error_code="REFRESH_TOKEN_EXPIRED",
                message="Refresh token has expired"
            )
        except JWTError as e:
            raise APIException(
                status_code=401,
                error_code="INVALID_REFRESH_TOKEN",
                message=f"Invalid refresh token: {str(e)}"
            )
        except JWTClaimsError as e:
            raise APIException(
                status_code=401,
                error_code="INVALID_TOKEN_CLAIMS",
                message=f"Invalid token claims: {str(e)}"
            )
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to decode refresh token: {e}")
            raise APIException(
                status_code=500,
                error_code="TOKEN_DECODE_ERROR",
                message="Failed to decode refresh token"
            )
    
    def decode_access_token(self, access_token: str) -> Dict[str, Any]:
        """
        Decode and validate an access token.
        
        Args:
            access_token: Access token string
            
        Returns:
            Decoded token payload
            
        Raises:
            APIException: If token is invalid or expired
        """
        from constants import AUTH_SECRET_KEY, AUTH_ALGORITHM
        
        try:
            # First try to decode with validation
            try:
                payload = jwt.decode(
                    access_token,
                    AUTH_SECRET_KEY,
                    algorithms=[AUTH_ALGORITHM],
                    options={
                        "verify_signature": True,
                        "verify_exp": False,  # We'll check manually
                        "verify_iat": False,  # Disable iat validation
                        "verify_nbf": False,
                        "verify_aud": False,
                        "verify_iss": False,
                    }
                )
            except JWTError as e:
                # Try to decode without validation
                logger.warning(f"Token validation failed: {e}, attempting to decode without validation")
                try:
                    payload = jwt.decode(
                        access_token,
                        AUTH_SECRET_KEY,
                        algorithms=[AUTH_ALGORITHM],
                        options={
                            "verify_signature": False,
                            "verify_exp": False,
                            "verify_iat": False,
                            "verify_nbf": False,
                            "verify_aud": False,
                            "verify_iss": False,
                        }
                    )
                    logger.warning("Token decoded without validation")
                except Exception as e2:
                    logger.error(f"Failed to decode token even without validation: {e2}")
                    raise APIException(
                        status_code=401,
                        error_code="INVALID_TOKEN_FORMAT",
                        message=f"Invalid token format: {str(e2)}"
                    )
            
            # Normalize claims
            payload = self._normalize_claims(payload)
            
            # Verify it's an access token
            token_type = payload.get("token_type")
            if token_type not in ["access", None]:
                raise APIException(
                    status_code=401,
                    error_code="INVALID_TOKEN_TYPE",
                    message="Invalid token type",
                    details={"expected": "access", "received": token_type}
                )
            
            # Check if expired manually
            exp = payload.get("exp")
            if exp:
                try:
                    exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    
                    # Allow 5 seconds clock skew
                    clock_skew = 5
                    if exp_datetime < now_utc:
                        if (now_utc - exp_datetime).total_seconds() <= clock_skew:
                            logger.debug(f"Token expired but within clock skew ({clock_skew}s)")
                        else:
                            logger.warning(f"Token expired at {exp_datetime} (now: {now_utc})")
                            raise APIException(
                                status_code=401,
                                error_code="ACCESS_TOKEN_EXPIRED",
                                message="Access token has expired",
                                details={"expired_at": exp_datetime.isoformat()}
                            )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid exp claim: {exp} - {e}")
                    raise APIException(
                        status_code=401,
                        error_code="INVALID_TOKEN_EXPIRATION",
                        message="Invalid token expiration"
                    )
            
            # Check required fields
            if "app_user_id" not in payload:
                raise APIException(
                    status_code=401,
                    error_code="INVALID_TOKEN",
                    message="Invalid access token: missing user ID"
                )
            
            return payload
            
        except ExpiredSignatureError:
            raise APIException(
                status_code=401,
                error_code="ACCESS_TOKEN_EXPIRED",
                message="Access token has expired"
            )
        except JWTError as e:
            raise APIException(
                status_code=401,
                error_code="INVALID_ACCESS_TOKEN",
                message=f"Invalid access token: {str(e)}"
            )
        except JWTClaimsError as e:
            raise APIException(
                status_code=401,
                error_code="INVALID_TOKEN_CLAIMS",
                message=f"Invalid token claims: {str(e)}"
            )
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to decode access token: {e}")
            raise APIException(
                status_code=500,
                error_code="TOKEN_DECODE_ERROR",
                message="Failed to decode access token"
            )
    
    # ==================== Token Refresh ====================
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New access token and refresh token pair
            
        Raises:
            APIException: If refresh token is invalid
        """
        try:
            logger.info(f"token: {refresh_token}")
            # Decode and validate the refresh token
            payload = self.decode_refresh_token(refresh_token)
            
            logger.info(f"token: {json.dumps(payload)}")

            user_id = payload.get("app_user_id")
            # username = payload.get("username")
            # email = payload.get("email")
            
            if not user_id :
                raise APIException(
                    status_code=401,
                    error_code="INVALID_TOKEN_PAYLOAD",
                    message="Invalid refresh token payload"
                )
            
            # Optional: Get updated user info from database
            user = self.user_repo.get_by_id(user_id)
            if user:
                email = user.app_user_email
                username = user.app_user_name
            
            # Generate new token pair
            token_pair = self.generate_token_pair(user_id, username, email)
            
            logger.info(f"Access token refreshed for user {username} (user_id: {user_id})")
            
            return token_pair
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise APIException(
                status_code=500,
                error_code="REFRESH_FAILED",
                message="Failed to refresh access token"
            )
    
    # ==================== OAuth Methods ====================
    
    async def get_oauth_user_info(self, provider: str, token: dict) -> Optional[Dict[str, Any]]:
        """Fetch user information from OAuth provider."""
        
        if provider == "google":
            return await self._get_google_user_info(token)
        elif provider == "facebook":
            return await self._get_facebook_user_info(token)
        elif provider == "instagram":
            return await self._get_instagram_user_info(token)
        
        return None
    
    async def _get_google_user_info(self, token: dict) -> Optional[Dict[str, Any]]:
        """Fetch Google user info."""
        user_info = token.get("userinfo")
        if user_info:
            return {
                "id": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "provider": "google"
            }
        
        # Fallback: fetch from userinfo endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token['access_token']}"}
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": data.get("id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture"),
                    "provider": "google"
                }
        return None
    
    async def _get_facebook_user_info(self, token: dict) -> Optional[Dict[str, Any]]:
        """Fetch Facebook user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/me",
                params={
                    "fields": "id,name,email,picture",
                    "access_token": token["access_token"]
                }
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": data.get("id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture", {}).get("data", {}).get("url"),
                    "provider": "facebook"
                }
        return None
    
    async def _get_instagram_user_info(self, token: dict) -> Optional[Dict[str, Any]]:
        """Fetch Instagram user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.instagram.com/me",
                params={
                    "fields": "id,username,account_type",
                    "access_token": token["access_token"]
                }
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "id": data.get("id"),
                    "username": data.get("username"),
                    "email": None,
                    "name": data.get("username"),
                    "provider": "instagram"
                }
        return None
    
    async def handle_oauth_login(self, provider: str, request: Request, oauth_client) -> RedirectResponse:
        """Handle OAuth login redirect."""
        try:
            redirect_uri = f"{BASE_URL}/auth/{provider}"
            return await oauth_client.authorize_redirect(request, redirect_uri)
        
        except AttributeError as e:
            raise OAuthProviderNotSupportedException(
                provider=provider,
                supported_providers=self.get_supported_providers()
            )
        
        except ConnectionError as e:
            raise OAuthException(
                error=f"Connection failed: {str(e)}",
                provider=provider,
                details={"error_type": "connection_error"}
            )
        
        except TimeoutError as e:
            raise OAuthException(
                error=f"Timeout: {str(e)}",
                provider=provider,
                details={"error_type": "timeout"}
            )
        
        except ValueError as e:
            raise OAuthException(
                error=f"Configuration error: {str(e)}",
                provider=provider,
                details={"error_type": "configuration_error"}
            )
        
        except Exception as e:
            raise OAuthException(
                error=str(e),
                provider=provider,
                details={
                    "error_type": "unexpected_error",
                    "exception_type": e.__class__.__name__
                }
            )
    
    async def handle_oauth_callback(self, provider: str, request: Request, oauth_client) -> RedirectResponse:
        """Handle OAuth callback and process user authentication."""
        try:
            # Get access token from provider
            token = await oauth_client.authorize_access_token(request)
            
            # Get user info from provider
            user_info = await self.get_oauth_user_info(provider, token)
            if not user_info:
                return self.create_redirect_response({}, error="Failed to retrieve user information")
            
            # Store user in session
            request.session["user"] = user_info
            
            # Create or get user in your system
            user = await self.get_or_create_oauth_user(user_info, provider)
            
            # Generate token pair
            token_pair = self.generate_token_pair(
                user_id=user.id_app_user,
                username=user.app_user_name,
                email=user.app_user_email
            )
            
            # Prepare response data with tokens
            response_data = self.prepare_user_response(user, token_pair)
            
            return self.create_redirect_response(response_data)
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return self.create_redirect_response({}, error=str(e))
    
    async def get_or_create_oauth_user(self, user_info: Dict[str, Any], provider: str):
        """Get existing user or create a new one from OAuth data."""
        
        email = user_info.get("email")
        if not email and provider == "instagram":
            email = f"{user_info.get('id')}@instagram.user"
        
        # Check if user exists
        # existing_user = self.user_service.get_user_by_email(email)
        existing_user = None  # Placeholder until user_service is integrated
        
        if existing_user:
            return existing_user
        
        # Create new user
        app_user = AppUser_API(
            id_app_user=0,
            app_user_name=email,
            app_user_password=self.generate_random_password(),
            app_user_person_id=None,
            app_user_preferences=None,
            app_user_image_url=user_info.get("picture"),
            app_user_email=email,
            app_user_type=2  # Default user type for OAuth users
        )
        
        # return await self.user_service.create_user(app_user, provider=provider)
        return app_user  # Placeholder
    
    def prepare_user_response(self, user, token_pair: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare user response data with tokens."""
        
        # Convert user object to dictionary
        if hasattr(user, '__dict__'):
            user_dict = user.__dict__
            user_dict.pop('_sa_instance_state', None)
        elif hasattr(user, 'dict'):
            user_dict = user.dict()
        else:
            user_dict = dict(user)
        
        # Remove sensitive data
        user_dict.pop('app_user_password', None)
        
        return {
            "success": True,
            "user": user_dict,
            "tokens": token_pair
        }
    
    # ==================== Authentication Methods ====================
    
    async def login_user(self, auth_data: AuthData_API) -> Dict[str, Any]:
        """
        Authenticate user and return access token.
        """
        try:
            # Call auth server to authenticate
            result = await self.auth_client.login(
                username=auth_data.app_user_name,
                user_id=auth_data.id_app_user,
                password=auth_data.app_user_password
            )
            
            logger.info(f"User {auth_data.app_user_name} authenticated successfully")
            
            # Generate refresh token
            refresh_token = self.generate_refresh_token(
                user_id=auth_data.id_app_user,
                username=auth_data.app_user_name
            )
            
            # Add refresh token to response
            result["refresh_token"] = refresh_token
            result["refresh_token_expires_in"] = self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            
            return result
            
        except AuthLoginException as e:
            logger.error(f"Login failed for {auth_data.app_user_name}: {e}")
            raise
    
    async def change_user_password(
        self,
        user_id: int,
        username: str,
        new_password: str,
        token: str
    ) -> Dict[str, Any]:
        """Change user password through auth server."""
        response = await self.auth_manager.change_password(
            user_id=user_id,
            username=username,
            new_password=new_password,
            token=token
        )
        
        new_password_hash = response.get("hashed_password")
        
        user = self.user_repo.get_by_id(user_id)
        user.app_user_password = new_password_hash

        try:
            return self.user_repo.update(user)
        except Exception as e:
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_UPDATE_FAILED,
                details={"user_id": user.id_app_user, "error": str(e)}
            )

    
    async def delete_user(self, user_id: int, username: str, password: str) -> None:
        """Delete user from auth server."""
        await self.auth_client.delete_user(user_id, username, password)
    
    def logout_user(self, request: Request) -> Dict[str, Any]:
        """Log out user by clearing session."""
        request.session.clear()
        return {"success": True, "message": "Logged out successfully"}
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without raising exceptions.
        
        Args:
            token: JWT token
            
        Returns:
            True if token is expired, False otherwise
        """
        from constants import AUTH_SECRET_KEY, AUTH_ALGORITHM
        
        try:
            payload = jwt.decode(
                token,
                AUTH_SECRET_KEY,
                algorithms=[AUTH_ALGORITHM],
                options={"verify_exp": False}
            )
            
            exp = payload.get("exp")
            if exp:
                exp_value = self._parse_timestamp(exp)
                if exp_value is not None:
                    exp_datetime = datetime.fromtimestamp(exp_value, tz=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    return exp_datetime < now_utc
            return False
            
        except Exception:
            return True
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get the expiry time of a token.
        
        Args:
            token: JWT token
            
        Returns:
            Expiry datetime or None if not found
        """
        from constants import AUTH_SECRET_KEY, AUTH_ALGORITHM
        
        try:
            payload = jwt.decode(
                token,
                AUTH_SECRET_KEY,
                algorithms=[AUTH_ALGORITHM],
                options={"verify_exp": False}
            )
            
            exp = payload.get("exp")
            if exp:
                exp_value = self._parse_timestamp(exp)
                if exp_value is not None:
                    return datetime.fromtimestamp(exp_value, tz=timezone.utc)
            return None
            
        except Exception:
            return None
    
    def get_token_remaining_time(self, token: str) -> Optional[int]:
        """
        Get the remaining time (in seconds) until token expires.
        
        Args:
            token: JWT token
            
        Returns:
            Remaining seconds or None if not found
        """
        expiry = self.get_token_expiry(token)
        if expiry:
            now_utc = datetime.now(timezone.utc)
            remaining = int((expiry - now_utc).total_seconds())
            return max(0, remaining)
        return None