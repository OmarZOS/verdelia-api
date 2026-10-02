# app/auth.py
from asyncio.log import logger
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Any, Dict, Optional
from core.messages import *
from fastapi import Depends,  status
from sqlalchemy.orm import Session
from constants import ACCESS_TOKEN_EXPIRE_MINUTES,  REFRESH_TOKEN_EXPIRE_DAYS ,API_ALGORITHM,API_SECRET_KEY




def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token from client data.
    
    Args:
        data: Data to encode in token (from auth server)
        expires_delta: Optional custom expiration
    
    Returns:
        JWT token string
    """
    import time
    from datetime import datetime, timedelta, timezone
    
    to_encode = data.copy()
    
    # Get current time as integer timestamp
    now = int(time.time())
    
    # Set expiration as integer timestamp
    if expires_delta:
        expire = now + int(expires_delta.total_seconds())
    else:
        expire = now + int(timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds())
    
    # Add standard JWT claims as integers
    to_encode.update({"exp": expire})
    to_encode.update({"iat": now})
    
    # Optional: Add issuer if not present
    if "iss" not in to_encode:
        to_encode.update({"iss": "verdelia-auth-server"})
    
    # Log for debugging
    logger.debug(f"Creating token with exp: {expire} (type: {type(expire)})")
    logger.debug(f"Creating token with iat: {now} (type: {type(now)})")
    
    # Encode JWT - no need to convert datetimes
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm=API_ALGORITHM)
    
    logger.debug(f"Access token created for user {data.get('app_user_id')}")
    return encoded_jwt

def convert_datetimes(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(item) for item in obj]
    else:
        return obj

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token from client data.
    """
    to_encode = data.copy()
    to_encode.update({"token_type": "refresh"})
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=int(REFRESH_TOKEN_EXPIRE_DAYS))
    
    to_encode.update({"exp": expire})
    to_encode.update({"iat": datetime.utcnow()})
    
    to_encode = convert_datetimes(to_encode)
    
    encoded_jwt = jwt.encode(to_encode, API_SECRET_KEY, algorithm=API_ALGORITHM)
    
    logger.debug(f"Refresh token created for user {data.get('app_user_id')}")
    return encoded_jwt