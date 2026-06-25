from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user, CurrentUser, security
from fastapi.security import HTTPAuthorizationCredentials
from supabase import AsyncClient
from app.database import (
    get_user_client,
    get_service_role_client,
    list_threads,
    create_thread,
    get_thread,
    update_thread,
    delete_thread,
    get_messages,
    get_message_citations,
)
from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID

router = APIRouter()


async def get_supabase_client(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AsyncClient:
    """Dependency to retrieve a user-scoped Supabase client."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    return await get_user_client(credentials.credentials)


async def verify_thread_access(thread_id: UUID, user_id: str) -> dict[str, Any]:
    """Helper to verify thread existence and ownership (raises 404/403)."""
    service_client = await get_service_role_client()
    thread = await get_thread(service_client, thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    if str(thread.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this thread is forbidden"
        )
    return thread


class CreateThreadRequest(BaseModel):
    title: Optional[str] = None


class UpdateThreadRequest(BaseModel):
    title: str


@router.get("/threads")
async def get_threads(
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        return await list_threads(client, user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list threads: {str(e)}"
        )


@router.post("/threads")
async def post_thread(
    body: CreateThreadRequest,
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        return await create_thread(client, user.id, body.title)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create thread: {str(e)}"
        )


@router.get("/threads/{thread_id}")
async def get_single_thread(
    thread_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        return await verify_thread_access(thread_id, user.id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve thread: {str(e)}"
        )


@router.patch("/threads/{thread_id}")
async def patch_thread(
    thread_id: UUID,
    body: UpdateThreadRequest,
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        await verify_thread_access(thread_id, user.id)
        return await update_thread(client, thread_id, body.title)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update thread: {str(e)}"
        )


@router.delete("/threads/{thread_id}")
async def delete_single_thread(
    thread_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        await verify_thread_access(thread_id, user.id)
        success = await delete_thread(client, thread_id)
        return {"success": success}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete thread: {str(e)}"
        )


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        await verify_thread_access(thread_id, user.id)
        messages = await get_messages(client, thread_id)
        
        # Enrich assistant messages with citations
        for msg in messages:
            if msg.get("role") == "assistant":
                citations = await get_message_citations(client, msg["id"])
                if not msg.get("payload"):
                    msg["payload"] = {}
                
                formatted_citations = []
                for citation in citations:
                    metadata = citation.get("citation_metadata", {})
                    formatted_citations.append({
                        "index": citation.get("citation_index"),
                        "company": metadata.get("company", "Unknown"),
                        "filing_type": metadata.get("filing_type", "Unknown"),
                        "year": metadata.get("year", "Unknown"),
                        "section": metadata.get("section", "Unknown"),
                        "page": metadata.get("page", "Unknown"),
                        "excerpt": metadata.get("excerpt", "")
                    })
                msg["payload"]["citations"] = formatted_citations
                
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}"
        )
