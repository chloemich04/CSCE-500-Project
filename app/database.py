"""Database connection via DATABASE_URL (PostgreSQL) or SQLite for local dev."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    url = settings.database_url
    
    # If DATABASE_URL is empty or not set, use SQLite for local development
    if not url or url.startswith("sqlite"):
        url = "sqlite:///./minishop.db"
        _engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        # PostgreSQL (Supabase)
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        _engine = create_engine(url, pool_pre_ping=True)
    
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=_engine)
    
    return _engine


def get_db():
    get_engine()
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
