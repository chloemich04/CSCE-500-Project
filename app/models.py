"""SQLAlchemy table mapping and Pydantic request/response shapes."""

from sqlalchemy import Column, Integer, String, DateTime, func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
