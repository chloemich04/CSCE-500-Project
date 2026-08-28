import os
from fastapi import FastAPI
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends 
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt

# Configuration for password hashing (move this to "app/core/config.py" later)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
router = APIRouter(prefix="/api/auth", tags=["auth"])

_users = {}

# Request and Response Models
class RegisterRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Utility functions for password hashing and token creation
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# API Endpoints
@router.post("/register")
async def register(req: RegisterRequest):
    if req.email in _users:
        raise HTTPException(status_code=400, detail="User already exists")
    
    _users[req.email] ={"password_hash": hash_password(req.password)}
    return {"message": "User registered successfully"}

@router.post("/login", response_model=TokenResponse)
async def login(req: RegisterRequest):
    user = _users.get(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials. Email or password is incorrect.")
    
    token = create_access_token({"sub": req.email})
    return {"access_token": token}


