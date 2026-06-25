"""Database models, clients, and CRUD operations."""

from app.database.base import Base
from app.database.models import (
    ChatMessage,
    ChatThread,
    DocumentChunk,
    MessageCitation,
    SourceDocument,
    User,
)
from app.database.supabase import (
    get_service_role_client,
    get_user_client,
)
from app.database.chats import (
    create_thread,
    get_thread,
    list_threads,
    update_thread,
    delete_thread,
    create_message,
    get_messages,
    create_citations,
    get_message_citations,
)

__all__ = [
    "Base",
    "User",
    "ChatThread",
    "ChatMessage",
    "MessageCitation",
    "SourceDocument",
    "DocumentChunk",
    "get_service_role_client",
    "get_user_client",
    "create_thread",
    "get_thread",
    "list_threads",
    "update_thread",
    "delete_thread",
    "create_message",
    "get_messages",
    "create_citations",
    "get_message_citations",
]

