import pytest
from app.retrieval.queries import vector_search, lexical_search
from app.retrieval.types import RetrievalFilter
from app.retrieval.embeddings import embed_query

def test_lexical_search_real_data(db_session):
    """Test full-text search against real ingested database data."""
    results = lexical_search(db_session, "iPhone revenue services mix", limit=5)
    assert len(results) > 0
    for chunk in results:
        assert chunk.text is not None
        assert chunk.document is not None
        assert chunk.document.ticker in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

def test_vector_search_real_data(db_session):
    """Test pgvector similarity search against real ingested database data."""
    query_emb = embed_query("NVIDIA export control risks graphics processors China")
    results = vector_search(db_session, query_emb, limit=5)
    assert len(results) > 0
    for chunk in results:
        assert chunk.text is not None
        assert chunk.document is not None
        assert chunk.document.ticker in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

def test_queries_with_filters(db_session):
    """Test search operations with ticker and fiscal year filters."""
    filters = RetrievalFilter(tickers=["AAPL"], fiscal_years=[2024])
    
    # Verify lexical filters
    results_lexical = lexical_search(db_session, "services net sales margin", limit=5, filters=filters)
    for chunk in results_lexical:
        assert chunk.document.ticker == "AAPL"
        assert chunk.document.fiscal_year == 2024
        
    # Verify vector filters
    query_emb = embed_query("services net sales margin")
    results_vector = vector_search(db_session, query_emb, limit=5, filters=filters)
    for chunk in results_vector:
        assert chunk.document.ticker == "AAPL"
        assert chunk.document.fiscal_year == 2024
