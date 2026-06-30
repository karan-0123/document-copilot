from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload, Session
from app.database.models import DocumentChunk

def get_chunk_by_id(db: Session, chunk_id: UUID) -> DocumentChunk | None:
    """Retrieve a single document chunk by its unique ID, loading document metadata."""
    stmt = (
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.id == chunk_id)
    )
    return db.execute(stmt).scalar_one_or_none()

def get_chunk_with_neighbors(
    db: Session, chunk_id: UUID, before: int = 1, after: int = 1
) -> list[DocumentChunk]:
    """Retrieve a target document chunk and its contiguous surrounding chunks.
    
    This preserves the natural narrative context in sequential document sections.
    """
    target = get_chunk_by_id(db, chunk_id)
    if not target:
        return []
        
    stmt = (
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .where(DocumentChunk.document_id == target.document_id)
        .where(DocumentChunk.chunk_index >= max(0, target.chunk_index - before))
        .where(DocumentChunk.chunk_index <= target.chunk_index + after)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(db.execute(stmt).scalars().all())
