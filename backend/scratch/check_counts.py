import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models import SourceDocument, DocumentChunk

def main():
    engine = create_engine(settings.sqlalchemy_database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        doc_count = session.query(func.count(SourceDocument.id)).scalar()
        chunk_count = session.query(func.count(DocumentChunk.id)).scalar()
        print(f"Total SourceDocuments: {doc_count}")
        print(f"Total DocumentChunks: {chunk_count}")
        
        # Print a few sample chunks
        chunks = session.query(DocumentChunk).limit(3).all()
        for idx, c in enumerate(chunks, 1):
            print(f"Chunk {idx}: document_id={c.document_id}, index={c.chunk_index}, text={c.text[:100]}...")

if __name__ == "__main__":
    main()
