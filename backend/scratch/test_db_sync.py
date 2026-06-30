import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

def main():
    print("Testing Sync DB connection...")
    print("DB URL:", settings.sqlalchemy_database_url)
    engine = create_engine(settings.sqlalchemy_database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1"))
        print("Result:", result.scalar())
        
        # Test query on source_documents
        from app.database.models import SourceDocument
        stmt = select(SourceDocument).limit(1)
        res = session.execute(stmt)
        doc = res.scalar_one_or_none()
        if doc:
            print("Found doc:", doc.company_name, doc.ticker, doc.fiscal_year)
        else:
            print("No docs found.")

if __name__ == "__main__":
    main()
