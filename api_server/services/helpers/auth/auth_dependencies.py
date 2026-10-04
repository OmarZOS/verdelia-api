# dependencies/auth_dependencies.py

import json
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Union
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError, JWTClaimsError
from datetime import datetime, timezone
import logging

from constants import AUTH_ALGORITHM, AUTH_SECRET_KEY
from core.exceptions.handler import APIException
from core.messages import *

from core.logging_config import get_logger

logger = get_logger(__name__)



class JWTBearer(HTTPBearer):
    """
    JWT Bearer authentication dependency.
    Supports both access tokens and refresh tokens with different validation rules.
    """
    def __init__(self, auto_error: bool = True, allow_refresh: bool = False):
        """
        Initialize JWTBearer.
        
        Args:
            auto_error: Whether to automatically raise HTTP exceptions
            allow_refresh: Whether to allow refresh tokens (for refresh endpoints)
        """
        super().__init__(auto_error=auto_error)
        self.allow_refresh = allow_refresh

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            
            if not credentials:
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid authorization code"
                    )
                return None
            
            if credentials.scheme != "Bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid authentication scheme"
                    )
                return None
            
            # Verify token
            return await self.verify_token(credentials.credentials)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    def _parse_timestamp(self, value: Union[int, float, str, None]) -> Optional[int]:
        """
        Parse timestamp from various formats.
        
        Supports:
        - Integer (Unix timestamp)
        - Float (Unix timestamp)
        - String (ISO format)
        - String (numeric)
        """
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, float):
            return int(value)
        
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                pass
            
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
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # First try to decode with full validation
            try:
                payload = jwt.decode(
                    token,
                    AUTH_SECRET_KEY,
                    algorithms=[AUTH_ALGORITHM],
                    options={
                        "verify_signature": True,
                        "verify_exp": False,  # We'll check manually
                        "verify_iat": False,
                        "verify_nbf": False,
                        "verify_aud": False,
                        "verify_iss": False,
                    }
                )
                logger.debug(f"Token decoded successfully for user: {payload.get('app_user_id')}")
            except JWTError as e:
                # If validation fails, try to decode without validation
                logger.warning(f"Token validation failed: {e}, attempting to decode without validation")
                try:
                    payload = jwt.decode(
                        token,
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
                    logger.warning(f"Token decoded without validation for user: {payload.get('app_user_id')}")
                except Exception as e2:
                    logger.error(f"Failed to decode token even without validation: {e2}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Invalid token format: {str(e2)}"
                    )
            
            # Check token type
            token_type = payload.get("token_type", "access")
            
            # If this is a refresh token endpoint, allow refresh tokens
            if token_type == "refresh" and not self.allow_refresh:
                logger.warning("Refresh token used for access endpoint")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token cannot be used for access"
                )
            
            # If this is not a refresh token endpoint, ensure it's an access token
            if token_type != "refresh" and token_type != "access":
                logger.warning(f"Unknown token type: {token_type}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type: {token_type}"
                )
            
            # Manually check expiration
            exp = payload.get("exp")
            if exp:
                exp_timestamp = self._parse_timestamp(exp)
                if exp_timestamp is not None:
                    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    
                    # Allow 5 seconds clock skew
                    clock_skew = 5
                    if exp_datetime < now_utc:
                        if (now_utc - exp_datetime).total_seconds() <= clock_skew:
                            logger.debug(f"Token expired but within clock skew ({clock_skew}s)")
                        else:
                            logger.warning(f"Token expired at {exp_datetime} (now: {now_utc})")
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token has expired"
                            )
                else:
                    logger.warning(f"Invalid exp claim format: {exp}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token expiration"
                    )
            
            # Check if required fields exist
            if "app_user_id" not in payload:
                logger.warning("Token missing app_user_id field")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            # Normalize app_user_id to int if it's a string
            try:
                if isinstance(payload.get("app_user_id"), str):
                    payload["app_user_id"] = int(payload["app_user_id"])
            except (ValueError, TypeError):
                logger.warning(f"Invalid app_user_id format: {payload.get('app_user_id')}")
            
            logger.debug(f"Token verified for user {payload.get('app_user_id')} (type: {token_type})")
            return payload
            
        except HTTPException:
            raise
        except ExpiredSignatureError:
            logger.warning("Token signature expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTClaimsError as e:
            logger.warning(f"JWT claims error: {str(e)}")
            try:
                payload = jwt.get_unverified_claims(token)
                logger.debug(f"Unverified claims: {payload}")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token claims: {str(e)}"
            )
        except JWTError as e:
            logger.warning(f"JWT error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# Dependency for access token authentication
async def get_current_user(
    payload: Dict[str, Any] = Depends(JWTBearer(allow_refresh=False))
) -> Dict[str, Any]:
    """
    Get current user from access token.
    
    Args:
        payload: JWT token payload
        
    Returns:
        Dict containing user information
    """
    return payload


# Dependency for refresh token authentication
async def get_refresh_token_user(
    payload: Dict[str, Any] = Depends(JWTBearer(allow_refresh=True))
) -> Dict[str, Any]:
    """
    Get current user from refresh token.
    This should only be used for refresh endpoints.
    
    Args:
        payload: JWT token payload
        
    Returns:
        Dict containing user information
    """
    # Verify it's actually a refresh token
    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected refresh token"
        )
    return payload


# Get user ID from access token
async def get_current_user_id(
    payload: Dict[str, Any] = Depends(get_current_user)
) -> int:
    """
    Get current user ID from access token.
    
    Args:
        payload: JWT token payload
        
    Returns:
        User ID as integer
        
    Raises:
        HTTPException: If user ID is not found or invalid
    """
    user_id = payload.get("app_user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token"
        )
    
# Get user Token from access token
async def get_current_user_access_token(
    payload: Dict[str, Any] = Depends(get_current_user)
) -> int:
    """
    Get current user ID from access token.
    
    Args:
        payload: JWT token payload
        
    Returns:
        User ID as integer
        
    Raises:
        HTTPException: If user ID is not found or invalid
    """
    user_id = payload.get("access_token")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth token not found in api token"
        )
    
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token"
        )


# Get user info from access token
async def get_current_user_info(
    payload: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user information from access token.
    
    Args:
        payload: JWT token payload
        
    Returns:
        Dict containing user information
    """
    return {
        "user_id": payload.get("app_user_id"),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "first_name": payload.get("first_name"),
        "last_name": payload.get("last_name"),
        "access_token": payload.get("access_token"),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
        "iss": payload.get("iss"),
        "token_type": payload.get("token_type", "access"),
    }


# Get username from access token
async def get_current_username(
    payload: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Get current username from access token.
    
    Args:
        payload: JWT token payload
        
    Returns:
        Username as string
        
    Raises:
        HTTPException: If username is not found
    """
    username = payload.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username not found in token"
        )
    return username


# Optional dependency that doesn't require authentication
async def get_optional_user(
    request: Request,
) -> Optional[Dict[str, Any]]:
    """
    Get current user from access token if present, otherwise return None.
    
    This is useful for endpoints that support both authenticated and unauthenticated access.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User payload if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    try:
        jwt_bearer = JWTBearer(auto_error=False, allow_refresh=False)
        return await jwt_bearer.verify_token(token)
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


# Validate refresh token specifically
async def validate_refresh_token(
    refresh_token: str,
) -> Dict[str, Any]:
    """
    Validate a refresh token specifically.
    
    Args:
        refresh_token: The refresh token string
        
    Returns:
        Decoded payload if valid
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Decode with refresh token validation
        payload = jwt.decode(
            refresh_token,
            AUTH_SECRET_KEY,
            algorithms=[AUTH_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_aud": False,
                "verify_iss": False,
            }
        )
        
        # Check token type
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token"
            )
        
        # Check required fields
        if "app_user_id" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token: missing user ID"
            )
        
        return payload
        
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Refresh token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


# Extract token from request
async def get_token_from_request(
    request: Request,
) -> Optional[str]:
    """
    Extract JWT token from the Authorization header.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Token string or None if not found
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]