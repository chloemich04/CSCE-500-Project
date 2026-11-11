"""Register and login (M6: through the user directory, then the user's shard)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_directory_db, new_id, open_user_shard, shard_of
from app.models import User, UserDirectory
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, directory: Session = Depends(get_directory_db)):
    email = body.email.strip().lower()
    user_id = new_id()

    # Step 1: claim the email in the directory (email is its primary key = global uniqueness).
    directory.add(UserDirectory(email=email, user_id=user_id))
    try:
        directory.commit()
    except IntegrityError:
        directory.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Step 2: create the user on its own shard. If that fails, release the email.
    db = open_user_shard(user_id)
    try:
        db.add(User(id=user_id, email=email, password_hash=hash_password(body.password),
                    account_type=body.account_type))
        db.commit()
    except Exception:
        db.rollback()
        directory.query(UserDirectory).filter(UserDirectory.email == email).delete()
        directory.commit()
        raise
    finally:
        db.close()

    return {"id": str(user_id), "email": email, "account_type": body.account_type,
            "shard": shard_of(user_id)}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, directory: Session = Depends(get_directory_db)):
    email = body.email.strip().lower()
    entry = directory.get(UserDirectory, email)
    if entry is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    db = open_user_shard(entry.user_id)
    try:
        user = db.get(User, entry.user_id)
    finally:
        db.close()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {"access_token": create_access_token(user.id, user.email, user.account_type)}
