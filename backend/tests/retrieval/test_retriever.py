import pytest
from app.database import get_chunk_with_neighbors
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import RetrievalFilter

def test_document_retriever_search(db_session):
    """Test the DocumentRetriever search_filings orchestration end-to-end."""
    retriever = DocumentRetriever()
    
    # Query specific to Amazon AWS
    results = retriever.search_filings(
        db_session,
        "What is Amazon AWS segment operating income?",
        filters=RetrievalFilter(tickers=["AMZN"]),
        limit=5
    )
    
    assert len(results) > 0
    assert len(results) <= 5
    for passage in results:
        assert passage.ticker == "AMZN"
        assert passage.text is not None
        assert passage.score is not None
        assert passage.source_url is not None
        assert passage.company_name == "Amazon.com, Inc."

def test_get_chunk_with_neighbors_real_data(db_session):
    """Test fetching a chunk and its immediate logical sequential neighbors."""
    retriever = DocumentRetriever()
    results = retriever.search_filings(
        db_session,
        "Apple services net sales",
        limit=1
    )
    assert len(results) > 0
    target_passage = results[0]
    
    # Retrieve target chunk + 1 chunk before + 1 chunk after
    neighbors = get_chunk_with_neighbors(
        db_session,
        target_passage.chunk_id,
        before=1,
        after=1
    )
    
    assert len(neighbors) > 0
    
    # Verify that neighbor chunks are sequential and from the same document context
    indices = [c.chunk_index for c in neighbors]
    assert indices == sorted(indices)
    assert len(indices) <= 3  # at most before + target + after = 3
    
    # Verify they all belong to the same document
    for c in neighbors:
        assert c.document_id == target_passage.document_id
        assert c.document.ticker == target_passage.ticker
