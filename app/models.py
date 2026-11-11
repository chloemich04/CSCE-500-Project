"""SQLAlchemy mapping of the sharded schema (M6). Every id is a uuid.

The authoritative Postgres DDL is M6/sql/01_shard_schema.sql (CHECKs, shard_bucket,
checkout procedure). These classes mirror it; create_all is only used for SQLite tests.
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base

# ---------- catalog: copied on every shard, same ids everywhere ----------

product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", Uuid, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Uuid, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    products = relationship("Product", secondary=product_categories, back_populates="categories")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("stock >= 0", name="products_stock_nonnegative"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    # Stock is NOT a copy: each shard holds its own allocation of the units
    # (sum over shards = real stock), so checkout stays a 1-shard transaction.
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    categories = relationship("Category", secondary=product_categories, back_populates="products")


# ---------- customer-owned: all rows of one user on that user's shard ----------


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CartItem(Base):
    """No carts table any more: the cart IS the user's cart_items rows (keyed by user_id)."""

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    product_id = Column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, CheckConstraint("quantity > 0"), nullable=False)

    product = relationship("Product")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("user_id", "id"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String, nullable=False, default="placed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("OrderItem", back_populates="order", foreign_keys="OrderItem.order_id",
                         primaryjoin="Order.id == OrderItem.order_id")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        ForeignKeyConstraint(["user_id", "order_id"], ["orders.user_id", "orders.id"]),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, nullable=False)  # copied from the order so the row routes by itself
    order_id = Column(Uuid, nullable=False)
    product_id = Column(Uuid, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_at_order = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items", foreign_keys=[order_id],
                         primaryjoin="Order.id == OrderItem.order_id")
    product = relationship("Product")


# ---------- directory DB only (shard_0): used by login and sign-up ----------


class UserDirectory(Base):
    __tablename__ = "user_directory"

    email = Column(Text, primary_key=True)  # lower-cased
    user_id = Column(Uuid, nullable=False, unique=True, default=uuid.uuid4)


class BucketMap(Base):
    __tablename__ = "bucket_map"

    bucket = Column(Integer, primary_key=True)
    shard = Column(Text, nullable=False)
