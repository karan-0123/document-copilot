from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Create engine using the computed SQLAlchemy database URL (with psycopg driver)
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# SessionLocal is the factory for synchronous DB sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db():
    """FastAPI dependency to get a synchronous database session.
    
    Automatically runs inside FastAPI's thread pool when used as a dependency.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
