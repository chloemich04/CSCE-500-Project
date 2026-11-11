"""Load settings from environment variables (and a local .env file)."""

import os

from dotenv import load_dotenv

load_dotenv()


def _url(name: str, fallback: str = "") -> str:
    url = (os.getenv(name) or fallback).strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Settings:
    # M6: connection strings live in config, never in code.
    # SHARD_0_URL falls back to the old DATABASE_URL; DIRECTORY_URL falls back to SHARD_0_URL.
    database_url: str = _url("DATABASE_URL")
    shard_0_url: str = _url("SHARD_0_URL", database_url)
    shard_1_url: str = _url("SHARD_1_URL")
    directory_url: str = _url("DIRECTORY_URL", shard_0_url)
    # Postgres schema holding the tables on every shard ("shard" = sharded setup,
    # "single" = the one-database baseline used for the "before" load test).
    shard_schema: str = os.getenv("SHARD_SCHEMA", "shard")
    # SHARD_COUNT=1 forces every bucket onto shard_0 even if SHARD_1_URL is set.
    shard_count: int = int(os.getenv("SHARD_COUNT") or (2 if _url("SHARD_1_URL") else 1))

    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))

    jwt_secret: str = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "change-me"
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM") or os.getenv("ALGORITHM") or "HS256"
    jwt_expire_minutes: int = int(
        os.getenv("JWT_EXPIRE_MINUTES") or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") or "60"
    )
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
