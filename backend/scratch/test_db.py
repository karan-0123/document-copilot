import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from app.config import settings

async def main():
    print("Testing DB connection...")
    print("DB URL:", settings.sqlalchemy_database_url)
    engine = create_async_engine(settings.sqlalchemy_database_url)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(text("SELECT 1"))
        print("Result:", result.scalar())
        
        # Test query on source_documents
        from app.database.models import SourceDocument
        stmt = select(SourceDocument).limit(1)
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if doc:
            print("Found doc:", doc.company_name, doc.ticker, doc.fiscal_year)
        else:
            print("No docs found.")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
