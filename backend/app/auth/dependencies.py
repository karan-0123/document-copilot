import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from app.database import get_user_client, get_service_role_client
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

        # Sync user to the public.users database table to prevent FK violations
        user_id = response.user.id
        email = response.user.email

        service_client = await get_service_role_client()
        existing = (
            await service_client.table("users").select("id").eq("id", user_id).execute()
        )
        if not existing.data:
            await (
                service_client.table("users")
                .insert({"id": user_id, "email": email})
                .execute()
            )

        return CurrentUser(
            id=user_id,
            email=email,
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
