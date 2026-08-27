"""Register and login JSON endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        account_type=body.account_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "account_type": user.account_type,
    }


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id, user.email, user.account_type)
    return {"access_token": token}
