from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, Session
from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.types import RetrievalFilter

def vector_search(
    db: Session,
    query_embedding: list[float],
    limit: int = 50,
    filters: RetrievalFilter | None = None,
) -> list[DocumentChunk]:
    """Execute a semantic vector similarity search on document chunks using pgvector.
    
    Includes optional filters for tickers and fiscal years.
    """
    stmt = (
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .join(SourceDocument)
        .where(DocumentChunk.embedding.isnot(None))
    )
    
    # Apply optional metadata filters
    if filters:
        if filters.tickers:
            stmt = stmt.where(SourceDocument.ticker.in_(filters.tickers))
        if filters.fiscal_years:
            stmt = stmt.where(SourceDocument.fiscal_year.in_(filters.fiscal_years))
        if filters.filing_types:
            stmt = stmt.where(SourceDocument.filing_type.in_(filters.filing_types))
            
    # Order by vector cosine similarity distance ascending (closer distance = higher similarity)
    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding).asc())
    stmt = stmt.limit(limit)
    
    return list(db.execute(stmt).scalars().all())

def lexical_search(
    db: Session,
    query_text: str,
    limit: int = 50,
    filters: RetrievalFilter | None = None,
) -> list[DocumentChunk]:
    """Execute a keyword-based lexical search on document chunks using Postgres Full-Text Search.
    
    First attempts a strict websearch query (logical AND across terms). If no results are found,
    it falls back to a logical OR query across alphanumeric terms to ensure retrieval coverage.
    """
    cleaned_query = query_text.strip()
    if not cleaned_query:
        return []
        
    # 1. Attempt strict websearch FTS query (English)
    tsquery = func.websearch_to_tsquery("english", cleaned_query)
    
    stmt = (
        select(DocumentChunk)
        .options(selectinload(DocumentChunk.document))
        .join(SourceDocument)
        .where(DocumentChunk.search_vector.op("@@")(tsquery))
    )
    
    # Apply optional metadata filters
    if filters:
        if filters.tickers:
            stmt = stmt.where(SourceDocument.ticker.in_(filters.tickers))
        if filters.fiscal_years:
            stmt = stmt.where(SourceDocument.fiscal_year.in_(filters.fiscal_years))
        if filters.filing_types:
            stmt = stmt.where(SourceDocument.filing_type.in_(filters.filing_types))
            
    stmt = stmt.order_by(func.ts_rank_cd(DocumentChunk.search_vector, tsquery).desc())
    stmt = stmt.limit(limit)
    
    results = list(db.execute(stmt).scalars().all())
    
    # 2. Fallback to broad OR search if strict search returns nothing
    if not results:
        # Extract alphanumeric words and ignore single characters
        words = [
            w for w in cleaned_query.replace("'", "").replace('"', "").split()
            if w.isalnum() and len(w) > 1
        ]
        if words:
            or_query = " | ".join(words)
            tsquery_or = func.to_tsquery("english", or_query)
            
            stmt_or = (
                select(DocumentChunk)
                .options(selectinload(DocumentChunk.document))
                .join(SourceDocument)
                .where(DocumentChunk.search_vector.op("@@")(tsquery_or))
            )
            
            if filters:
                if filters.tickers:
                    stmt_or = stmt_or.where(SourceDocument.ticker.in_(filters.tickers))
                if filters.fiscal_years:
                    stmt_or = stmt_or.where(SourceDocument.fiscal_year.in_(filters.fiscal_years))
                if filters.filing_types:
                    stmt_or = stmt_or.where(SourceDocument.filing_type.in_(filters.filing_types))
                    
            stmt_or = stmt_or.order_by(func.ts_rank_cd(DocumentChunk.search_vector, tsquery_or).desc())
            stmt_or = stmt_or.limit(limit)
            
            results = list(db.execute(stmt_or).scalars().all())
            
    return results
