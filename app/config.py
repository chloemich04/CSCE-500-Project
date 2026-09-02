"""Load settings from environment variables (and a local .env file)."""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    jwt_secret: str = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "change-me"
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM") or os.getenv("ALGORITHM") or "HS256"
    jwt_expire_minutes: int = int(
        os.getenv("JWT_EXPIRE_MINUTES") or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") or "60"
    )
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
