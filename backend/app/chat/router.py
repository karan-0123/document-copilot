from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.auth.dependencies import get_current_user, CurrentUser, security
from fastapi.security import HTTPAuthorizationCredentials
from supabase import AsyncClient
from app.database import (
    get_user_client,
    get_service_role_client,
    get_thread,
    create_message,
    get_messages,
)
from pydantic import BaseModel
from typing import Optional, List, Any
import json
import asyncio
from uuid import UUID

router = APIRouter()


class MessageParam(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    messages: List[MessageParam]
    thread_id: str

    model_config = {
        "extra": "ignore"
    }


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


# Stubs definitions
APPLE_REPLY = (
    "In Apple's 2025 10-K, the iPhone segment represented 51% of total revenue. "
    "Net Sales in the services sector rose by 12% YoY, confirming the shift to services monetization. "
    "Multi-year data center CapEx commits rose significantly."
)
APPLE_CITATIONS = [{
    "index": 1,
    "company": "Apple Inc.",
    "filing_type": "10-K",
    "year": 2025,
    "section": "Item 7 - Management's Discussion and Analysis",
    "page": "44",
    "excerpt": "iPhone net sales represented 51% of total net sales. Services net sales increased 12% compared to the prior year."
}]

NVIDIA_REPLY = (
    "In NVIDIA's recent filings, export restrictions relating to high-performance computing graphics processors (e.g., A100/H100) to China remain a critical risk. "
    "Mitigation involves developing compliant chips (e.g., H20) but they carry lower margins and competitive risks."
)
NVIDIA_CITATIONS = [{
    "index": 1,
    "company": "NVIDIA Corp.",
    "filing_type": "10-K",
    "year": 2025,
    "section": "Item 1A - Risk Factors",
    "page": "18",
    "excerpt": "New export control regulations could permanently restrict our ability to design and sell chips in major global regions."
}]

DEFAULT_REPLY = (
    "Based on my retrieval search of your internal filings, Amazon's AWS division accounts for over 65% of operating income. "
    "CapEx investments on AI server capacity rose by 32% YoY."
)
DEFAULT_CITATIONS = [{
    "index": 1,
    "company": "Amazon.com, Inc.",
    "filing_type": "10-K",
    "year": 2024,
    "section": "Item 7 - Segment Results",
    "page": "32",
    "excerpt": "AWS segment operating income represented approximately 66% of consolidated operating income."
}]


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user: CurrentUser = Depends(get_current_user),
):
    # 1. 403 / 404 Thread Access Check
    try:
        thread_uuid = UUID(body.thread_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread_id UUID format"
        )

    service_client = await get_service_role_client()
    thread = await get_thread(service_client, thread_uuid)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

    if str(thread.get("user_id")) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this thread is forbidden"
        )

    # Determine last user message and stub details
    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided in request history"
        )

    last_user_message = body.messages[-1].content
    
    # Select response stub based on prompt contents
    prompt_lower = last_user_message.lower()
    if "apple" in prompt_lower:
        reply_text = APPLE_REPLY
        citations = APPLE_CITATIONS
    elif "nvidia" in prompt_lower:
        reply_text = NVIDIA_REPLY
        citations = NVIDIA_CITATIONS
    else:
        reply_text = DEFAULT_REPLY
        citations = DEFAULT_CITATIONS

    # 2. Generator to stream response in AI SDK data stream format
    async def event_generator() -> AsyncGenerator[str, None]:
        words = reply_text.split(" ")
        accumulated_reply = ""
        
        # Stream the words chunk by chunk
        for i, word in enumerate(words):
            chunk = word
            # Add back space between words except the last one
            if i < len(words) - 1:
                chunk += " "
            accumulated_reply += chunk
            
            # Format: 0:"text"\n (AI SDK text protocol)
            yield f'0:{json.dumps(chunk)}\n'
            await asyncio.sleep(0.04)

        # After successfully streaming the complete text:
        # Fetch existing messages count to get the correct sequence numbers
        existing = await get_messages(service_client, thread_uuid)
        seq_user = len(existing) + 1
        seq_assistant = len(existing) + 2

        # Persist user message
        await create_message(
            service_client,
            thread_id=thread_uuid,
            role="user",
            content=last_user_message,
            sequence=seq_user
        )

        # Persist assistant message with citations inside payload
        await create_message(
            service_client,
            thread_id=thread_uuid,
            role="assistant",
            content=accumulated_reply,
            sequence=seq_assistant,
            payload={"citations": citations}
        )

    # Return stream
    return StreamingResponse(
        event_generator(),
        media_type="text/plain; charset=utf-8",
        headers={"x-experimental-stream-data": "true"}
    )
