import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config import settings
from app.database.base import Base

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.database.models.source_document import SourceDocument
    from app.database.models.message_citation import MessageCitation


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[str | None] = mapped_column(String(64))
    section: Mapped[str | None] = mapped_column(String(255))
    token_count: Mapped[int | None] = mapped_column(Integer)
    chunk_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=sa_text("'{}'::jsonb")
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.openai_embedding_dimensions)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["SourceDocument"] = relationship(back_populates="chunks")
    citations: Mapped[list["MessageCitation"]] = relationship(back_populates="chunk")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_doc_index"),
        Index("ix_document_chunks_document_id", "document_id"),
    )
