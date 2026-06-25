import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from app.database import get_user_client
from supabase import AuthApiError

logger = logging.getLogger("app.auth")
security = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: str
    email: EmailStr


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    """FastAPI dependency to verify Supabase JWT token and return authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header or invalid token format",
        )

    token = credentials.credentials
    try:
        client = await get_user_client(token)
        response = await client.auth.get_user(token)
        
        if response is None or response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
            
        return CurrentUser(
            id=response.user.id,
            email=response.user.email,
        )

    except HTTPException:
        raise
    except AuthApiError as e:
        logger.warning(f"Auth verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth verification failed: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication service error",
        )
