import pytest
from app.database import SessionLocal

@pytest.fixture(scope="session", autouse=True)
def mock_openai_embeddings(monkeypatch_session):
    """Intercepts and mocks all OpenAI embedding API calls globally at the SDK class level.
    
    This ensures that any test calling client.embeddings.create (like during ingestion,
    retrieval, or queries) does not make real network calls and is immune to RateLimitErrors.
    """
    import openai.resources.embeddings
    
    class MockData:
        def __init__(self, embedding):
            self.embedding = embedding
            
    class MockResponse:
        def __init__(self, data):
            self.data = data
            
    def mock_create(self, *args, **kwargs):
        input_data = kwargs.get("input", [])
        if isinstance(input_data, str):
            input_data = [input_data]
        return MockResponse([MockData([0.1] * 768) for _ in input_data])
        
    monkeypatch_session.setattr(
        openai.resources.embeddings.Embeddings,
        "create",
        mock_create
    )

@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch helper."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()

@pytest.fixture(scope="module")
def db_session():
    """Module-scoped database session fixture that wraps tests in a transaction.
    
    Provisions a few DocumentChunks with mock embeddings for testing vector queries,
    and rolls back the transaction upon completion to keep the database state clean.
    """
    db = SessionLocal()
    # Start a transaction block
    db.begin()
    try:
        from app.database.models import DocumentChunk, SourceDocument
        from sqlalchemy import select
        
        # 1. Provision Apple 2024 chunks with mock embeddings for filter tests
        stmt = (
            select(DocumentChunk)
            .join(SourceDocument)
            .where(SourceDocument.ticker == "AAPL")
            .where(SourceDocument.fiscal_year == 2024)
            .limit(10)
        )
        chunks = list(db.execute(stmt).scalars().all())
        
        # 2. Fallback to any chunks if Apple 2024 chunks are not found
        if not chunks:
            chunks = list(db.execute(select(DocumentChunk).limit(10)).scalars().all())
            
        for chunk in chunks:
            chunk.embedding = [0.1] * 768
            
        db.flush()  # Push mock embeddings to database transaction state
        
        yield db
    finally:
        # Roll back everything to leave the database clean
        db.rollback()
        db.close()
