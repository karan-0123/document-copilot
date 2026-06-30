import json
import asyncio
from uuid import UUID
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from supabase import AsyncClient

from app.auth.dependencies import get_current_user, CurrentUser, security
from app.database import (
    get_user_client,
    get_service_role_client,
    get_thread,
    create_message,
    get_messages,
    list_threads,
    create_thread,
    update_thread,
    delete_thread,
    get_message_citations,
)
from app.schemas import (
    ChatStreamRequest,
    CreateThreadRequest,
    UpdateThreadRequest,
)

chat_router = APIRouter()
chats_router = APIRouter()


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )
    if str(thread.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this thread is forbidden",
        )
    return thread


@chat_router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user: CurrentUser = Depends(get_current_user),
):
    # 1. Verify UUID format and permissions
    try:
        thread_uuid = UUID(body.thread_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread_id UUID format",
        )

    service_client = await get_service_role_client()
    thread = await get_thread(service_client, thread_uuid)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    if str(thread.get("user_id")) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this thread is forbidden",
        )

    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided in request history",
        )

    # 2. Invoke orchestrator to run LLM agent, validate grounding, stream response, and persist to database
    from app.chat.orchestrator import orchestrate_chat_turn

    # Return stream
    return StreamingResponse(
        orchestrate_chat_turn(
            thread_id=thread_uuid,
            user_id=str(user.id),
            client_messages=[m.model_dump() for m in body.messages]
        ),
        media_type="text/plain; charset=utf-8",
        headers={"x-experimental-stream-data": "true"},
    )


@chats_router.get("/threads")
async def get_threads(
    user: CurrentUser = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
):
    try:
        return await list_threads(client, user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list threads: {str(e)}",
        )


@chats_router.post("/threads")
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
            detail=f"Failed to create thread: {str(e)}",
        )


@chats_router.get("/threads/{thread_id}")
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
            detail=f"Failed to retrieve thread: {str(e)}",
        )


@chats_router.patch("/threads/{thread_id}")
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
            detail=f"Failed to update thread: {str(e)}",
        )


@chats_router.delete("/threads/{thread_id}")
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
            detail=f"Failed to delete thread: {str(e)}",
        )


@chats_router.get("/threads/{thread_id}/messages")
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
                    formatted_citations.append(
                        {
                            "index": citation.get("citation_index"),
                            "company": metadata.get("company", "Unknown"),
                            "filing_type": metadata.get("filing_type", "Unknown"),
                            "year": metadata.get("year", "Unknown"),
                            "section": metadata.get("section", "Unknown"),
                            "page": metadata.get("page", "Unknown"),
                            "excerpt": metadata.get("excerpt", ""),
                        }
                    )
                msg["payload"]["citations"] = formatted_citations

        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}",
        )
