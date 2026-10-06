# dependencies/user_dependencies.py
from fastapi import Depends, HTTPException, status
from typing import Any, Dict, Optional

from services.helpers.auth.auth_dependencies import JWTBearer
from repositories.user_repository import UserRepository
from core.models.models import AppUser

def get_user_repository() -> UserRepository:
    return UserRepository()

async def verify_user(
    payload: Dict[str, Any] = Depends(JWTBearer()),
    user_repo: UserRepository = Depends(get_user_repository)
) -> AppUser:
    """
    Verify user exists in database and return user object.
    """

    
    user_id = payload.get("app_user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    user = user_repo.get_by_id(user_id, eager_load=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user