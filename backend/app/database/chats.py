import uuid
from typing import Any
from uuid import UUID
from supabase import AsyncClient


async def create_thread(
    client: AsyncClient, user_id: UUID | str, title: str | None = None
) -> dict[str, Any]:
    """Create a new chat thread for a user."""
    payload = {"id": str(uuid.uuid4()), "user_id": str(user_id)}
    if title is not None:
        payload["title"] = title
    response = await client.table("chat_threads").insert(payload).execute()
    return response.data[0] if response.data else {}


async def get_thread(
    client: AsyncClient, thread_id: UUID | str
) -> dict[str, Any] | None:
    """Retrieve a thread by its ID."""
    response = (
        await client.table("chat_threads")
        .select("*")
        .eq("id", str(thread_id))
        .execute()
    )
    return response.data[0] if response.data else None


async def list_threads(
    client: AsyncClient, user_id: UUID | str
) -> list[dict[str, Any]]:
    """List all threads for a user, ordered by updated_at descending."""
    response = (
        await client.table("chat_threads")
        .select("*")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def update_thread(
    client: AsyncClient, thread_id: UUID | str, title: str
) -> dict[str, Any]:
    """Update a thread's title."""
    response = (
        await client.table("chat_threads")
        .update({"title": title})
        .eq("id", str(thread_id))
        .execute()
    )
    return response.data[0] if response.data else {}


async def delete_thread(client: AsyncClient, thread_id: UUID | str) -> bool:
    """Delete a thread. Returns True if deleted successfully, False otherwise."""
    response = (
        await client.table("chat_threads").delete().eq("id", str(thread_id)).execute()
    )
    return len(response.data) > 0


async def create_message(
    client: AsyncClient,
    thread_id: UUID | str,
    role: str,
    content: str,
    sequence: int,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a chat message."""
    data = {
        "id": str(uuid.uuid4()),
        "thread_id": str(thread_id),
        "role": role,
        "content": content,
        "sequence": sequence,
    }
    if payload is not None:
        data["payload"] = payload
    response = await client.table("chat_messages").insert(data).execute()
    return response.data[0] if response.data else {}


async def get_messages(
    client: AsyncClient, thread_id: UUID | str
) -> list[dict[str, Any]]:
    """Get all messages in a thread, ordered by sequence ascending."""
    response = (
        await client.table("chat_messages")
        .select("*")
        .eq("thread_id", str(thread_id))
        .order("sequence", desc=False)
        .execute()
    )
    return response.data


async def create_citations(
    client: AsyncClient,
    message_id: UUID | str,
    citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create citations for a message.

    Each citation dict in the list should contain:
      - chunk_id: UUID or str
      - citation_index: int
      - citation_metadata: dict (optional)
    """
    payload = []
    for citation in citations:
        payload.append(
            {
                "id": str(uuid.uuid4()),
                "message_id": str(message_id),
                "chunk_id": str(citation["chunk_id"]),
                "citation_index": citation["citation_index"],
                "citation_metadata": citation.get("citation_metadata", {}),
            }
        )
    if not payload:
        return []
    response = await client.table("message_citations").insert(payload).execute()
    return response.data


async def get_message_citations(
    client: AsyncClient, message_id: UUID | str
) -> list[dict[str, Any]]:
    """Get citations for a message, ordered by citation_index ascending."""
    response = (
        await client.table("message_citations")
        .select("*")
        .eq("message_id", str(message_id))
        .order("citation_index", desc=False)
        .execute()
    )
    return response.data
