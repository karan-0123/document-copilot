from sqlalchemy.orm import Session
from app.config import settings
from app.database.models import DocumentChunk
from app.retrieval.types import RetrievalFilter, SourcePassage, SearchFilters
from app.retrieval.embeddings import embed_query
from app.retrieval.queries import vector_search, lexical_search
from app.retrieval.fusion import reciprocal_rank_fusion

def map_chunk_to_passage(chunk: DocumentChunk, score: float | None = None) -> SourcePassage:
    """Map a database DocumentChunk ORM object to the SourcePassage Pydantic model."""
    doc = chunk.document
    return SourcePassage(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        text=chunk.text,
        ticker=doc.ticker,
        company_name=doc.company_name,
        filing_type=doc.filing_type,
        fiscal_year=doc.fiscal_year,
        page=chunk.page,
        section=chunk.section,
        score=score,
        source_url=doc.source_url,
    )

class DocumentRetriever:
    """Orchestrates the hybrid retrieval pipeline by fusing semantic and keyword search.
    
    Acts as the main retrieval access boundary for LLM agents and debug routes.
    """
    
    def search_filings(
        self,
        db: Session,
        query: str,
        filters: RetrievalFilter | None = None,
        limit: int | None = None,
        candidate_k: int | None = None,
    ) -> list[SourcePassage]:
        """Runs vector and full-text searches, applies RRF fusion, and returns ranked SourcePassages."""
        if not query.strip():
            return []
            
        search_limit = limit or settings.retrieval_limit
        cand_k = candidate_k or settings.retrieval_candidate_k
        
        # 1. Generate query embedding
        query_embedding = embed_query(query)
        
        # 2. Execute parallel search branches
        vector_results = vector_search(db, query_embedding, limit=cand_k, filters=filters)
        lexical_results = lexical_search(db, query, limit=cand_k, filters=filters)
        
        # 3. Fuse rankings using RRF
        fused = reciprocal_rank_fusion(vector_results, lexical_results, k=settings.rrf_k)
        
        # 4. Limit candidate set to final top limit
        top_candidates = fused[:search_limit]
        
        # 5. Map to Pydantic SourcePassage models
        return [map_chunk_to_passage(chunk, score) for chunk, score in top_candidates]

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int | None = None,
        candidate_k: int | None = None,
    ) -> list[SourcePassage]:
        """Convenience search wrapper that handles the DB session automatically and accepts SearchFilters."""
        from app.database.session import SessionLocal
        
        ret_filters = None
        if filters:
            ret_filters = RetrievalFilter(
                tickers=[filters.ticker] if filters.ticker else None,
                filing_types=[filters.form] if filters.form else None,
            )
            
        with SessionLocal() as db:
            return self.search_filings(
                db=db,
                query=query,
                filters=ret_filters,
                limit=limit,
                candidate_k=candidate_k,
            )

