"""Database routing for the sharded store (M6).

Data placement (see M6/m6-report.md):
- every customer-owned row (users, cart_items, orders, order_items) lives on ONE shard,
  chosen from the hashed user id: bucket = md5(user_id)[:8] % 64, then bucket -> shard;
- the catalog (products, categories, product_categories) is copied on every shard;
- the login directory (email -> user_id) and bucket_map live on the directory DB (= shard_0).

Without any Postgres URL the app runs on one local SQLite file (1 shard), which the
unit tests also use.
"""

import hashlib
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

NUM_BUCKETS = 64

_engines: list = []
_sessions: list = []
_directory_session = None
_bucket_map: dict[int, int] = {}


def shard_bucket(user_id) -> int:
    """Same rule as the SQL function shard_bucket(uuid) installed on every shard."""
    return int(hashlib.md5(str(user_id).encode()).hexdigest()[:8], 16) % NUM_BUCKETS


def _default_bucket_map(shard_count: int) -> dict[int, int]:
    # Fixed buckets, contiguous ranges: 2 shards -> 0..31 on shard_0, 32..63 on shard_1.
    per_shard = NUM_BUCKETS // shard_count
    return {b: min(b // per_shard, shard_count - 1) for b in range(NUM_BUCKETS)}


def _make_engine(url: str, schema: str | None):
    if not url or url.startswith("sqlite"):
        engine = create_engine(
            url or "sqlite:///./minishop.db", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        return engine

    # Supabase session pooler (nano) caps clients per database: keep
    # workers x DB_POOL_SIZE under that cap (default 5, no overflow).
    engine = create_engine(url, pool_pre_ping=True, pool_size=settings.db_pool_size, max_overflow=0)
    if schema:
        # Tables live in a dedicated schema (shard / single); public keeps the pre-M6 data.
        @event.listens_for(engine, "connect")
        def _set_search_path(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute(f"SET search_path TO {schema}, public")
            cur.close()
            dbapi_conn.commit()

    return engine


def init_databases() -> None:
    global _directory_session, _bucket_map
    if _engines:
        return

    urls = [settings.shard_0_url]
    if settings.shard_count >= 2 and settings.shard_1_url:
        urls.append(settings.shard_1_url)

    schema = settings.shard_schema
    for url in urls:
        engine = _make_engine(url, schema)
        _engines.append(engine)
        _sessions.append(sessionmaker(bind=engine, autocommit=False, autoflush=False))

    if settings.directory_url == settings.shard_0_url:
        _directory_session = _sessions[0]
    else:
        _directory_session = sessionmaker(bind=_make_engine(settings.directory_url, schema))

    _bucket_map = _default_bucket_map(len(_engines))
    # The bucket_map table is the source of truth when it exists (moving a bucket = 1 UPDATE).
    try:
        with _directory_session() as db:
            rows = db.execute(text("SELECT bucket, shard FROM bucket_map")).all()
        if rows:
            names = {f"shard_{i}": i for i in range(len(_engines))}
            _bucket_map = {b: names.get(s, 0) for b, s in rows}
    except Exception:
        pass


def shard_count() -> int:
    init_databases()
    return len(_engines)


def shard_of(user_id) -> int:
    init_databases()
    return _bucket_map[shard_bucket(user_id)]


def open_shard(index: int) -> Session:
    init_databases()
    return _sessions[index]()


def open_user_shard(user_id) -> Session:
    return open_shard(shard_of(user_id))


def open_directory() -> Session:
    init_databases()
    return _directory_session()


@contextmanager
def all_shards():
    """One session per shard, for catalog writes that must land everywhere."""
    sessions = [open_shard(i) for i in range(shard_count())]
    try:
        yield sessions
    finally:
        for s in sessions:
            s.close()


def get_db():
    """Catalog reads for anonymous pages: any shard has the full catalog, use shard_0."""
    db = open_shard(0)
    try:
        yield db
    finally:
        db.close()


def get_directory_db():
    db = open_directory()
    try:
        yield db
    finally:
        db.close()


def new_id() -> uuid.UUID:
    return uuid.uuid4()


def reset_for_tests(engine) -> None:
    """Point the router at a single test engine (unit tests)."""
    global _directory_session, _bucket_map
    _engines.clear()
    _sessions.clear()
    _engines.append(engine)
    _sessions.append(sessionmaker(bind=engine, autocommit=False, autoflush=False))
    _directory_session = _sessions[0]
    _bucket_map = _default_bucket_map(1)
