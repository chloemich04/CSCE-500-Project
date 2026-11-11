"""Password hashing (Argon2), JWT helpers and the current-user dependency.

M6: the token carries the user id (uuid) and its shard. Every authenticated request
then opens a session on THAT shard only (step 10: one customer page = one shard).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import open_user_shard, shard_of

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id, email: str, account_type: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "shard": shard_of(user_id),
        "email": email,
        "account_type": account_type,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@dataclass
class CurrentUser:
    """Identity from the token + a session open on the user's own shard."""

    id: uuid.UUID
    email: str
    account_type: str
    db: Session


def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token>.",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    # The shard is recomputed from the id (bucket rule), never trusted from the token.
    db = open_user_shard(user_id)
    try:
        yield CurrentUser(
            id=user_id,
            email=payload.get("email", ""),
            account_type=payload.get("account_type", "customer"),
            db=db,
        )
    finally:
        db.close()


def require_manager(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.account_type != "store_manager":
        raise HTTPException(status_code=403, detail="Store manager access required.")
    return user
