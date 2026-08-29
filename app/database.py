"""PostgreSQL connection via DATABASE_URL (Supabase). No SQLite."""

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
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if not url:
        raise RuntimeError(
            "DATABASE_URL is missing. Copy .env.example to .env and set your Supabase URL."
        )

    _engine = create_engine(url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db():
    get_engine()
    db: Session = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
