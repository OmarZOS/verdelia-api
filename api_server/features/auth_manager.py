# clients/auth_manager.py

import logging
import time
from typing import Dict, Any, Optional
from threading import Lock

from core.logging_config import get_logger
from features.auth_client import AuthClient
from constants import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from core.exceptions.handler import (
    AuthLoginException,
    AuthTokenInvalidException,
    AuthServiceUnavailableException
)

from core.logging_config import get_logger

logger = get_logger(__name__)



class AuthManager:
    """
    Authentication Manager that handles:
    - System login with default admin credentials
    - Token storage and refresh for system user
    - Automatic token injection for password changes and user deletions
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AuthManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._auth_client = AuthClient()
        
        # System token storage
        self._system_token = None
        self._system_token_data = None
        self._system_token_expiry = None
        self._is_system_logged_in = False
        self._system_login_time = None
        
        # Token refresh buffer (5 minutes)
        self._refresh_buffer = 300
        
        logger.info("AuthManager initialized")
        
        # Auto-login with system credentials on initialization
        self._auto_login_system()
    
    def _auto_login_system(self) -> bool:
        """
        Automatically login with system credentials.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Check if system token already exists and is valid
            if self._is_system_token_valid():
                logger.info("System token already valid")
                self._is_system_logged_in = True
                return True
            
            # Login with system credentials
            logger.info("Auto-login with system credentials...")
            import asyncio
            
            # Run async login in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._auth_client.login(
                    username=DEFAULT_ADMIN_USERNAME,
                    user_id=0,  # Default admin user ID
                    password=DEFAULT_ADMIN_PASSWORD
                )
            )
            loop.close()
            
            # Store system token
            self._system_token = result.get("access_token")
            self._system_token_data = result
            self._system_token_expiry = result.get("expires_at")
            self._is_system_logged_in = True
            self._system_login_time = time.time()
            
            logger.info(f"System login successful for user: {DEFAULT_ADMIN_USERNAME}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to auto-login with system credentials: {e}")
            self._is_system_logged_in = False
            return False
    
    def _is_system_token_valid(self) -> bool:
        """
        Check if system token is valid (not expired).
        
        Returns:
            True if token exists and is valid
        """
        if not self._system_token:
            return False
        
        if not self._system_token_expiry:
            return False
        
        # Check if token is expired (with buffer)
        current_time = time.time()
        return current_time < (self._system_token_expiry - self._refresh_buffer)
    
    def _ensure_system_token(self) -> Optional[str]:
        """
        Ensure system token is valid, refresh if needed.
        
        Returns:
            Valid system access token or None
        """
        # Check if system token is valid
        if self._is_system_token_valid():
            return self._system_token
        
        # Token is invalid or expired, try to refresh
        logger.info("System token invalid/expired. Attempting refresh...")
        
        # Clear invalid token
        self._system_token = None
        self._system_token_data = None
        self._system_token_expiry = None
        self._is_system_logged_in = False
        
        # Try to login again
        if self._auto_login_system():
            return self._system_token
        
        logger.error("Failed to refresh system token")
        return None
    
    def get_system_token(self) -> Optional[str]:
        """
        Get valid system token.
        
        Returns:
            Valid system access token or None
        """
        return self._ensure_system_token()
    
    def get_system_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get headers with system authentication.
        
        Args:
            extra_headers: Optional extra headers to include
        
        Returns:
            Dictionary with authentication headers
        """
        token = self.get_system_token()
        if not token:
            logger.warning("No system token available for headers")
            return extra_headers or {}
        
        headers = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    async def login_system_async(self) -> Dict[str, Any]:
        """
        Async login with system credentials.
        
        Returns:
            Token data dictionary
        """
        try:
            result = await self._auth_client.login(
                username=DEFAULT_ADMIN_USERNAME,
                user_id=0,  # Default admin user ID
                password=DEFAULT_ADMIN_PASSWORD
            )
            
            # Store system token
            self._system_token = result.get("access_token")
            self._system_token_data = result
            self._system_token_expiry = result.get("expires_at")
            self._is_system_logged_in = True
            self._system_login_time = time.time()
            
            logger.info(f"System login successful for user: {DEFAULT_ADMIN_USERNAME}")
            return result
            
        except Exception as e:
            logger.error(f"System login failed: {e}")
            self._is_system_logged_in = False
            raise AuthLoginException(
                error=f"System login failed: {str(e)}",
                username=DEFAULT_ADMIN_USERNAME
            )
    
    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
        
        Returns:
            Registered user data
        """
        return await self._auth_client.register_user(user_data)
    
    async def login_user(self, username: str, user_id: int, password: str) -> Dict[str, Any]:
        """
        Login a user and return token.
        
        Args:
            username: Username
            user_id: User ID
            password: Password
        
        Returns:
            Token data dictionary
        """
        return await self._auth_client.login(username, user_id, password)
    
    async def change_password(
        self,
        user_id: int,
        username: str,
        new_password: str,
        token: Optional[str] = None,
        use_system_token: bool = True
    ) -> Dict[str, Any]:
        """
        Change user password.
        
        If token is not provided, uses system token.
        
        Args:
            user_id: User ID
            username: Username
            new_password: New password
            token: Optional user token (if not provided, uses system token)
            use_system_token: Whether to use system token as fallback
        
        Returns:
            Updated user data
        """
        # If token not provided, use system token
        if not token and use_system_token:
            token = self.get_system_token()
            if not token:
                logger.warning("No system token available, attempting to refresh...")
                token = self._ensure_system_token()
            
            if not token:
                raise AuthTokenInvalidException(
                    error="No valid token available for password change. Please login first.",
                    details={"requires_login": True}
                )
        
        if not token:
            raise AuthTokenInvalidException(
                error="No token provided for password change.",
                details={"requires_login": True}
            )
        
        return await self._auth_client.change_password(
            user_id=user_id,
            username=username,
            new_password=new_password,
            token=token
        )
    
    async def delete_user(
        self,
        user_id: int,
        username: str,
        token: Optional[str] = None,
        use_system_token: bool = True
    ) -> None:
        """
        Delete a user.
        
        If token is not provided, uses system token.
        
        Args:
            user_id: User ID
            username: Username
            token: Optional user token (if not provided, uses system token)
            use_system_token: Whether to use system token as fallback
        """
        # If token not provided, use system token
        if not token and use_system_token:
            token = self.get_system_token()
            if not token:
                logger.warning("No system token available, attempting to refresh...")
                token = self._ensure_system_token()
            
            if not token:
                raise AuthTokenInvalidException(
                    error="No valid token available for user deletion. Please login first.",
                    details={"requires_login": True}
                )
        
        if not token:
            raise AuthTokenInvalidException(
                error="No token provided for user deletion.",
                details={"requires_login": True}
            )
        
        await self._auth_client.delete_user(
            user_id=user_id,
            username=username,
            token=token
        )
    
    async def health_check(self) -> bool:
        """
        Check if authentication service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return await self._auth_client.health_check()
    
    def is_system_logged_in(self) -> bool:
        """
        Check if system is logged in.
        
        Returns:
            True if system token is valid
        """
        return self._is_system_token_valid() and self._is_system_logged_in
    
    def get_system_login_status(self) -> Dict[str, Any]:
        """
        Get system login status details.
        
        Returns:
            Dictionary with system login status
        """
        status = {
            "is_logged_in": self.is_system_logged_in(),
            "has_token": self._system_token is not None,
            "is_token_valid": self._is_system_token_valid(),
        }
        
        if self._system_token_data:
            status.update({
                "username": self._system_token_data.get("username"),
                "app_user_id": self._system_token_data.get("app_user_id"),
                "token_type": self._system_token_data.get("token_type"),
            })
        
        if self._system_token_expiry:
            status.update({
                "expires_at": self._system_token_expiry,
                "expires_in_seconds": max(0, self._system_token_expiry - time.time()),
            })
        
        if self._system_login_time:
            status["login_time"] = self._system_login_time
        
        return status
    
    def refresh_system_token(self) -> bool:
        """
        Force refresh system token.
        
        Returns:
            True if refresh successful, False otherwise
        """
        # Clear existing token
        self._system_token = None
        self._system_token_data = None
        self._system_token_expiry = None
        self._is_system_logged_in = False
        self._system_login_time = None
        
        # Try to login again
        return self._auto_login_system()
    
    async def refresh_system_token_async(self) -> bool:
        """
        Async force refresh system token.
        
        Returns:
            True if refresh successful, False otherwise
        """
        # Clear existing token
        self._system_token = None
        self._system_token_data = None
        self._system_token_expiry = None
        self._is_system_logged_in = False
        self._system_login_time = None
        
        try:
            await self.login_system_async()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh system token: {e}")
            return False
    
    def clear_system_token(self) -> None:
        """Clear system token."""
        self._system_token = None
        self._system_token_data = None
        self._system_token_expiry = None
        self._is_system_logged_in = False
        self._system_login_time = None
        logger.info("System token cleared")


# ==================== Singleton Convenience Functions ====================

_auth_manager_instance = None
_auth_manager_lock = Lock()


def get_auth_manager() -> AuthManager:
    """
    Get the singleton AuthManager instance.
    
    Returns:
        AuthManager instance
    """
    global _auth_manager_instance
    
    if _auth_manager_instance is None:
        with _auth_manager_lock:
            if _auth_manager_instance is None:
                _auth_manager_instance = AuthManager()
    
    return _auth_manager_instance


# ==================== Convenience Functions ====================

async def register_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new user."""
    manager = get_auth_manager()
    return await manager.register_user(user_data)


async def login_user(username: str, user_id: int, password: str) -> Dict[str, Any]:
    """Login a user."""
    manager = get_auth_manager()
    return await manager.login_user(username, user_id, password)


async def change_password(
    user_id: int,
    username: str,
    new_password: str,
    token: Optional[str] = None,
    use_system_token: bool = True
) -> Dict[str, Any]:
    """Change user password."""
    manager = get_auth_manager()
    return await manager.change_password(user_id, username, new_password, token, use_system_token)


async def delete_user(
    user_id: int,
    username: str,
    token: Optional[str] = None,
    use_system_token: bool = True
) -> None:
    """Delete a user."""
    manager = get_auth_manager()
    await manager.delete_user(user_id, username, token, use_system_token)


def get_system_token() -> Optional[str]:
    """Get valid system token."""
    manager = get_auth_manager()
    return manager.get_system_token()


def get_system_headers(extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Get headers with system authentication."""
    manager = get_auth_manager()
    return manager.get_system_headers(extra_headers)


def is_system_logged_in() -> bool:
    """Check if system is logged in."""
    manager = get_auth_manager()
    return manager.is_system_logged_in()


def get_system_login_status() -> Dict[str, Any]:
    """Get system login status."""
    manager = get_auth_manager()
    return manager.get_system_login_status()


def refresh_system_token() -> bool:
    """Force refresh system token."""
    manager = get_auth_manager()
    return manager.refresh_system_token()


async def refresh_system_token_async() -> bool:
    """Async force refresh system token."""
    manager = get_auth_manager()
    return await manager.refresh_system_token_async()


async def health_check() -> bool:
    """Check if authentication service is healthy."""
    manager = get_auth_manager()
    return await manager.health_check()