"""JSON bodies the API accepts and returns."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    account_type: Literal["customer", "store_manager"]


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    category: str | None = None
    platform: str | None = None
    price: float = Field(gt=0)
    stock: int = Field(ge=0)


class ProductUpdate(ProductCreate):
    pass


class ProductOut(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
