# clients/auth_client.py

import json
import logging
from typing import Dict, Any, Optional
from enum import Enum

from core.logging_config import get_logger
from communication.communication_broker import send_delete_request, send_post_request, send_put_request
from constants import (
    AUTH_SERVER_NAME,
    AUTH_PORT,
    AUTH_REGISTRATION_ENDPOINT,
    AUTH_LOGIN_ENDPOINT,
    AUTH_CHANGE_ENDPOINT,
    AUTH_DELETE_ENDPOINT
)
from core.exceptions.handler import (
    AuthServiceUnavailableException,
    AuthRegistrationException,
    AuthLoginException,
    AuthPasswordChangeException,
    AuthUserDeletionException,
    AuthTokenExpiredException,
    AuthTokenInvalidException,
    AuthNetworkException
)

from core.logging_config import get_logger

logger = get_logger(__name__)



class AuthEndpoint(str, Enum):
    """Authentication service endpoints"""
    REGISTRATION = "/auth/register"
    LOGIN = "/auth/login"
    CHANGE_PASSWORD = "/auth/change-password"
    DELETE_USER = "/auth/delete-user"


class AuthClient:
    """Client for external authentication server API calls"""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize AuthClient.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{AUTH_SERVER_NAME}:{AUTH_PORT}"
        self.registration_endpoint = AUTH_REGISTRATION_ENDPOINT
        self.login_endpoint = AUTH_LOGIN_ENDPOINT
        self.change_password_endpoint = AUTH_CHANGE_ENDPOINT
        self.delete_user_endpoint = AUTH_DELETE_ENDPOINT
        self.timeout = timeout
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate that required configuration is present"""
        if not AUTH_SERVER_NAME:
            logger.error("AUTH_SERVER_NAME not configured")
            raise AuthServiceUnavailableException(
                service="authentication",
                error="Server name not configured"
            )
        
        if not AUTH_PORT:
            logger.error("AUTH_PORT not configured")
            raise AuthServiceUnavailableException(
                service="authentication",
                error="Server port not configured"
            )
        
        logger.info(f"AuthClient initialized with base URL: {self.base_url}")
    
    def _get_endpoint_url(self, endpoint: AuthEndpoint) -> str:
        """Get full URL for an auth endpoint"""
        endpoint_map = {
            AuthEndpoint.REGISTRATION: self.registration_endpoint,  
            AuthEndpoint.LOGIN: self.login_endpoint,
            AuthEndpoint.CHANGE_PASSWORD: self.change_password_endpoint,
            AuthEndpoint.DELETE_USER: self.delete_user_endpoint
        }
        
        endpoint_path = endpoint_map.get(endpoint)
        if not endpoint_path:
            raise AuthServiceUnavailableException(
                service="authentication",
                error=f"Unknown endpoint: {endpoint}"
            )
        
        return f"{self.base_url}{endpoint_path}"
    
    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user with the authentication server.
        
        Based on OpenAPI spec UserCreate:
        - Required: username, app_user_id, password
        - Optional: email, first_name, last_name, phone_number, date_of_birth, gender, profile_picture, roles
        """
        url = self._get_endpoint_url(AuthEndpoint.REGISTRATION)
        username = user_data.get("username")
        
        logger.info(f"Registering user '{username}' with authentication service")
        logger.info(f"Sending to: {url}")
        logger.info(f"Request data: {json.dumps(user_data)}")
        
        try:
            response = await send_post_request(
                url, 
                json_data=user_data,
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully registered user '{username}'")
                return result
            
            elif response.status_code == 409:
                error_data = response.json() if response.text else {}
                error_code = error_data.get("code", "CONFLICT")
                error_message = error_data.get("message", "User already exists")
                details = error_data.get("details", {})
                
                raise AuthRegistrationException(
                    error=error_message,
                    username=username,
                    details={
                        "status_code": 409,
                        "error_code": error_code,
                        "server_response": error_data
                    }
                )
            
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                raise AuthRegistrationException(
                    error=f"Invalid registration data: {error_data.get('message', '')}",
                    username=username,
                    details={"status_code": 400, "response": error_data}
                )
            
            elif response.status_code == 422:
                error_data = response.json() if response.text else {}
                raise AuthRegistrationException(
                    error=f"Validation error: {error_data.get('message', '')}",
                    username=username,
                    details={"status_code": 422, "response": error_data}
                )
            
            else:
                raise AuthRegistrationException(
                    error=f"Validation error: {response.response.text}",
                    username=username,
                    details={"status_code": 422, "response": response.response.text}
                )
                # response.raise_for_status()
                 
                
        except AuthRegistrationException:
            raise
        except Exception as e:
            logger.error(f"Failed to register user '{username}': {e}")
            raise AuthRegistrationException(
                error=str(e),
                username=username,
                details={"endpoint": "registration"}
            )
    
    async def login(self, username: str, user_id: int, password: str) -> Dict[str, Any]:
        """
        Authenticate with auth server and return token.
        
        Based on OpenAPI spec:
        - Uses application/x-www-form-urlencoded
        - Required: username, password
        - Optional: grant_type, scope, client_id, client_secret
        """
        url = self._get_endpoint_url(AuthEndpoint.LOGIN)
        
        # The OAuth2 password flow expects form data
        form_data = {
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": "",
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        logger.info(f"Authenticating user '{username}' with auth server")

        logger.info(f"Request data: {json.dumps(form_data)}")

        
        try:
            response = await send_post_request(
                url,
                payload_data=form_data,
                headers=headers,
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully authenticated user '{username}'")
                return {
                    "access_token": result.get("access_token"),
                    "token_type": result.get("token_type", "bearer"),
                    "expires_in": result.get("expires_in", 3600),
                    "expires_at": result.get("expires_at"),
                    "app_user_id": result.get("app_user_id", str(user_id)),  # Auth server returns as string
                    "username": result.get("username", username),
                    "email": result.get("email"),
                    "first_name": result.get("first_name"),
                    "last_name": result.get("last_name"),
                    "iat": result.get("iat"),
                    "iss": result.get("iss"),
                }
            
            elif response.status_code in [401, 403]:
                error_data = response.json() if response.text else {}
                error_message = error_data.get("message") or error_data.get("detail") or error_data.get("error") or "Authentication failed"
                raise AuthLoginException(
                    error=error_message,
                    username=username,
                    details={
                        "status_code": response.status_code,
                        "error_code": error_data.get("error_code", "INVALID_CREDENTIALS")
                    }
                )
            
            elif response.status_code == 404:
                raise AuthLoginException(
                    error="User not found",
                    username=username,
                    details={"status_code": 404}
                )
            
            elif response.status_code == 422:
                error_data = response.json() if response.text else {}
                raise AuthLoginException(
                    error=f"Validation error: {error_data.get('message', '')}",
                    username=username,
                    details={"status_code": 422, "response": error_data}
                )
            
            else:
                response.raise_for_status()
                return response.json()
                
        except AuthLoginException:
            raise
        except Exception as e:
            logger.error(f"Auth client error: {e}")
            raise AuthLoginException(
                error=str(e) or "Authentication failed",
                username=username
            )
    
    async def change_password(
        self,
        user_id: int,
        username: str,
        new_password: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Update a user's password through the authentication server.
        
        Based on OpenAPI spec UserUpdate:
        - Requires authentication via Bearer token
        - Required: username, app_user_id
        - Optional: new_password, new_username, email, first_name, last_name, etc.
        """
        url = self._get_endpoint_url(AuthEndpoint.CHANGE_PASSWORD)
        
        # Only send fields that are allowed by the API
        user_update = {
            "username": username,
            "app_user_id": user_id,
        }
        
        # Add optional fields if they exist
        if new_password:
            user_update["new_password"] = new_password
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Changing password for user '{username}' (user_id: {user_id})")
        logger.debug(f"Request data: {user_update}")
        
        try:
            response = await send_post_request(
                url,
                json_data=user_update,
                headers=headers,
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully changed password for user '{username}'")
                return result
            
            elif response.status_code == 401:
                error_data = response.json() if response.text else {}
                error_detail = error_data.get("detail", "")
                if "expired" in error_detail.lower():
                    raise AuthTokenExpiredException(token=token)
                else:
                    raise AuthTokenInvalidException(error=error_detail or "Invalid token")
            
            elif response.status_code == 403:
                error_data = response.json() if response.text else {}
                raise AuthPasswordChangeException(
                    error=error_data.get("detail", "Not authorized to change this user's password"),
                    user_id=user_id,
                    username=username,
                    details={"status_code": 403, "response": error_data}
                )
            
            elif response.status_code == 404:
                error_data = response.json() if response.text else {}
                raise AuthPasswordChangeException(
                    error=error_data.get("detail", "User not found"),
                    user_id=user_id,
                    username=username,
                    details={"status_code": 404, "response": error_data}
                )
            
            elif response.status_code == 422:
                error_data = response.json() if response.text else {}
                raise AuthPasswordChangeException(
                    error=f"Validation error: {error_data.get('detail', '')}",
                    user_id=user_id,
                    username=username,
                    details={"status_code": 422, "response": error_data}
                )
            
            else:
                response.raise_for_status()
                return response.json()
                
        except (AuthTokenExpiredException, AuthTokenInvalidException, AuthPasswordChangeException):
            raise
        except Exception as e:
            logger.error(f"Password change failed for user '{username}': {e}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    raise AuthPasswordChangeException(
                        error=error_data.get("detail", str(e)),
                        user_id=user_id,
                        username=username,
                        details={"status_code": e.response.status_code, "response": error_data}
                    )
                except:
                    pass
            raise AuthPasswordChangeException(
                error=str(e) or "Failed to change password",
                user_id=user_id,
                username=username
            )
    
    async def delete_user(self, user_id: int, username: str, token: str) -> None:
        """
        Delete a user through the authentication server.
        
        Based on OpenAPI spec:
        - Requires authentication via Bearer token
        - Required: username, app_user_id
        """
        url = self._get_endpoint_url(AuthEndpoint.DELETE_USER)
        
        user_data = {
            "username": username,
            "app_user_id": user_id,
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Deleting user '{username}' (user_id: {user_id}) from authentication service")
        logger.debug(f"Request data: {user_data}")
        
        try:
            response = await send_delete_request(
                url,
                input_data=user_data,
                headers=headers,
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully deleted user '{username}'")
                return
            
            elif response.status_code == 401:
                error_data = response.json() if response.text else {}
                error_detail = error_data.get("detail", "")
                if "expired" in error_detail.lower():
                    raise AuthTokenExpiredException(token=token)
                else:
                    raise AuthTokenInvalidException(error=error_detail or "Invalid token")
            
            elif response.status_code == 403:
                error_data = response.json() if response.text else {}
                raise AuthUserDeletionException(
                    error=error_data.get("detail", "Not authorized to delete this user"),
                    user_id=user_id,
                    username=username,
                    details={"status_code": 403, "response": error_data}
                )
            
            elif response.status_code == 404:
                error_data = response.json() if response.text else {}
                raise AuthUserDeletionException(
                    error=error_data.get("detail", "User not found in authentication service"),
                    user_id=user_id,
                    username=username,
                    details={"status_code": 404, "response": error_data}
                )
            
            elif response.status_code == 422:
                error_data = response.json() if response.text else {}
                raise AuthUserDeletionException(
                    error=f"Validation error: {error_data.get('detail', '')}",
                    user_id=user_id,
                    username=username,
                    details={"status_code": 422, "response": error_data}
                )
            
            else:
                response.raise_for_status()
                
        except (AuthTokenExpiredException, AuthTokenInvalidException, AuthUserDeletionException):
            raise
        except Exception as e:
            logger.error(f"Failed to delete user '{username}': {e}")
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    raise AuthUserDeletionException(
                        error=error_data.get("detail", str(e)),
                        user_id=user_id,
                        username=username,
                        details={"status_code": e.response.status_code, "response": error_data}
                    )
                except:
                    pass
            raise AuthUserDeletionException(
                error=str(e),
                user_id=user_id,
                username=username
            )
    
    async def health_check(self) -> bool:
        """
        Check if authentication service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/metrics"
            response = await send_post_request(url)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Auth service health check failed: {e}")
            return False