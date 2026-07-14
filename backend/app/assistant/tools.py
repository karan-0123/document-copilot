from uuid import UUID
from pydantic_ai import RunContext
from sqlalchemy import select
from app.assistant.deps import DocumentAgentDeps
from app.database.models import DocumentChunk
from app.retrieval import RetrievalFilter
from app.retrieval.retriever import map_chunk_to_passage

async def search_filings(ctx: RunContext[DocumentAgentDeps], query: str) -> str:
    """Search the SEC filings database for relevant passages matching a query.
    
    Applies any active ticker or fiscal year constraints automatically.
    """
    filters = None
    if ctx.deps.tickers or ctx.deps.fiscal_years:
        filters = RetrievalFilter(
            tickers=ctx.deps.tickers,
            fiscal_years=ctx.deps.fiscal_years
        )
        
    passages = ctx.deps.retriever.search_filings(
        db=ctx.deps.db,
        query=query,
        filters=filters
    )
    
    # Track all retrieved passages in context dependencies for grounding validation
    for p in passages:
        ctx.deps.retrieved_passages[str(p.chunk_id)] = p
        
    if not passages:
        return "No matching filings found."
        
    formatted = []
    for p in passages:
        formatted.append(
            f"[Document: {p.company_name} ({p.ticker}) | Filing: {p.filing_type} {p.fiscal_year} | Section: {p.section} | Page: {p.page}]\n"
            f"Chunk ID: {p.chunk_id}\n"
            f"Text Content:\n{p.text}\n"
            f"--------------------------------------------------"
        )
    return "\n".join(formatted)

async def read_chunk(ctx: RunContext[DocumentAgentDeps], chunk_id: UUID) -> str:
    """Retrieve the full text of a single specific filing chunk by its unique ID."""
    stmt = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    chunk = ctx.deps.db.execute(stmt).scalar_one_or_none()
    if not chunk:
        return "Chunk not found."
        
    p = map_chunk_to_passage(chunk)
    ctx.deps.retrieved_passages[str(p.chunk_id)] = p
    return f"[Chunk ID: {p.chunk_id}]\nText Content:\n{chunk.text}"

async def read_chunks(ctx: RunContext[DocumentAgentDeps], chunk_ids: list[UUID]) -> str:
    """Retrieve the full text of multiple specific chunks in batch using their IDs."""
    stmt = select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
    chunks = ctx.deps.db.execute(stmt).scalars().all()
    if not chunks:
        return "No matching chunks found."
        
    formatted = []
    for c in chunks:
        p = map_chunk_to_passage(c)
        ctx.deps.retrieved_passages[str(p.chunk_id)] = p
        formatted.append(f"[Chunk ID: {p.chunk_id}]\nText Content:\n{c.text}\n---")
        
    return "\n".join(formatted)

async def read_surrounding_chunks(ctx: RunContext[DocumentAgentDeps], chunk_id: UUID) -> str:
    """Retrieve a target chunk and its immediate sequential before/after neighbor chunks to see surrounding context.
    
    Use this to read preceding or succeeding lines if document text split across chunks.
    """
    from app.database import get_chunk_with_neighbors
    
    chunks = get_chunk_with_neighbors(
        db=ctx.deps.db,
        chunk_id=chunk_id,
        before=1,
        after=1
    )
    
    if not chunks:
        return "Chunk context neighbors not found."
        
    formatted = []
    for c in chunks:
        p = map_chunk_to_passage(c)
        # Register in deps tracking
        ctx.deps.retrieved_passages[str(p.chunk_id)] = p
        
        is_target = c.id == chunk_id
        tag = " [TARGET CHUNK]" if is_target else ""
        formatted.append(
            f"[Chunk ID: {p.chunk_id} | Index: {c.chunk_index}{tag}]\n"
            f"Text Content:\n{c.text}\n"
            f"--------------------------------------------------"
        )
    return "\n".join(formatted)
