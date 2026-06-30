import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Mock OpenAI embeddings for the verification script since the key has no quota
import openai.resources.embeddings

class MockData:
    def __init__(self, embedding):
        self.embedding = embedding
        
class MockResponse:
    def __init__(self, data):
        self.data = data
        
def mock_create(*args, **kwargs):
    input_data = kwargs.get("input", [])
    if isinstance(input_data, str):
        input_data = [input_data]
    return MockResponse([MockData([0.1] * 1536) for _ in input_data])

openai.resources.embeddings.Embeddings.create = mock_create

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import get_chunk_with_neighbors
from app.retrieval import DocumentRetriever, RetrievalFilter

def main():
    print("Initializing Database Connection...")
    engine = create_engine(settings.sqlalchemy_database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    db = SessionLocal()
    
    # Temporarily set up mock embeddings on some document chunks to make vector search produce hits
    # inside this verification run. We will do this in a transaction block and roll it back.
    print("Beginning retrieval verification session...")
    db.begin()
    try:
        from app.database.models import DocumentChunk, SourceDocument
        from sqlalchemy import select
        
        # Give Apple and NVIDIA chunks some embeddings
        stmt_aapl = select(DocumentChunk).join(SourceDocument).where(SourceDocument.ticker == "AAPL").limit(10)
        stmt_nvda = select(DocumentChunk).join(SourceDocument).where(SourceDocument.ticker == "NVDA").limit(10)
        
        aapl_chunks = list(db.execute(stmt_aapl).scalars().all())
        nvda_chunks = list(db.execute(stmt_nvda).scalars().all())
        
        for c in aapl_chunks + nvda_chunks:
            c.embedding = [0.1] * 1536
        db.flush()
        
        retriever = DocumentRetriever()
        
        # Test Case 1: Apple Revenue Mix Query
        print("\n==================================================")
        print("TEST CASE 1: Query: 'Apple iPhone revenue services mix'")
        print("Filters: ticker=AAPL")
        print("==================================================")
        results = retriever.search_filings(
            db, 
            query="Apple iPhone revenue services mix", 
            filters=RetrievalFilter(tickers=["AAPL"]),
            limit=3
        )
        for idx, passage in enumerate(results, 1):
            print(f"\n{idx}. [{passage.ticker} {passage.fiscal_year} - RRF Score: {passage.score:.6f}]")
            print(f"   Section: {passage.section} | Page: {passage.page}")
            print(f"   Excerpt: {passage.text[:200]}...")
            
        # Test Case 2: NVIDIA China Export Risk Query
        print("\n==================================================")
        print("TEST CASE 2: Query: 'NVIDIA graphics processors export restrictions to China'")
        print("Filters: None")
        print("==================================================")
        results = retriever.search_filings(
            db, 
            query="NVIDIA graphics processors export restrictions to China", 
            limit=3
        )
        for idx, passage in enumerate(results, 1):
            print(f"\n{idx}. [{passage.ticker} {passage.fiscal_year} - RRF Score: {passage.score:.6f}]")
            print(f"   Section: {passage.section} | Page: {passage.page}")
            print(f"   Excerpt: {passage.text[:200]}...")
            
        # Test Case 3: Neighbors context test
        if results:
            target = results[0]
            print("\n==================================================")
            print(f"TEST CASE 3: Surrounding context neighbors lookup for chunk {target.chunk_id}")
            print("==================================================")
            neighbors = get_chunk_with_neighbors(db, target.chunk_id, before=1, after=1)
            print(f"Target Chunk Index: {[c.chunk_index for c in neighbors if c.id == target.chunk_id][0]}")
            print(f"Consecutive Indexes retrieved: {[c.chunk_index for c in neighbors]}")
            print(f"First chunk text snippet: {neighbors[0].text[:120]}...")
            if len(neighbors) > 1:
                print(f"Second chunk text snippet: {neighbors[1].text[:120]}...")
                
    finally:
        print("\nRolling back verification transaction changes...")
        db.rollback()
        db.close()
        print("Database connection clean.")

if __name__ == "__main__":
    main()
