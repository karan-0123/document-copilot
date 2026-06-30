import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models import DocumentChunk

def main():
    engine = create_engine(settings.sqlalchemy_database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        total = session.query(func.count(DocumentChunk.id)).scalar()
        non_null = session.query(func.count(DocumentChunk.id)).where(DocumentChunk.embedding.isnot(None)).scalar()
        print(f"Total chunks: {total}")
        print(f"Chunks with non-null embedding: {non_null}")

if __name__ == "__main__":
    main()
