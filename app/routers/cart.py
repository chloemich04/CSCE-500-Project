"""Cart JSON API. Maps to existing products table; does not create or alter it."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Session, joinedload, relationship

from app.config import settings
from app.database import Base, get_db
from app.models import Product, User

router = APIRouter(prefix="/api/cart", tags=["cart"])


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id"),)

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")


class AddCartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token>.",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return user


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def load_cart(db: Session, user_id: int) -> Cart:
    get_or_create_cart(db, user_id)
    return (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .filter(Cart.user_id == user_id)
        .first()
    )


def _money(value) -> float:
    return float(Decimal(str(value)))


def serialize_cart(cart: Cart) -> dict:
    items = []
    total = Decimal("0")
    for item in cart.items:
        price = Decimal(str(item.product.price))
        line = price * item.quantity
        total += line
        items.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.product.name,
                "price": _money(price),
                "quantity": item.quantity,
                "line_total": _money(line),
            }
        )
    return {"cart_id": cart.id, "items": items, "total": _money(total)}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_cart(
    body: AddCartItemRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == body.product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    if product.stock is not None and body.quantity > product.stock:
        raise HTTPException(status_code=400, detail="Not enough stock.")

    cart = get_or_create_cart(db, user.id)
    item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.product_id == body.product_id)
        .first()
    )
    if item:
        new_qty = item.quantity + body.quantity
        if product.stock is not None and new_qty > product.stock:
            raise HTTPException(status_code=400, detail="Not enough stock.")
        item.quantity = new_qty
    else:
        item = CartItem(cart_id=cart.id, product_id=body.product_id, quantity=body.quantity)
        db.add(item)

    db.commit()
    return serialize_cart(load_cart(db, user.id))


@router.get("")
def get_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return serialize_cart(load_cart(db, user.id))


@router.put("/{item_id}")
def update_cart_item(
    item_id: int,
    body: UpdateCartItemRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cart = get_or_create_cart(db, user.id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    if item.product.stock is not None and body.quantity > item.product.stock:
        raise HTTPException(status_code=400, detail="Not enough stock.")
    item.quantity = body.quantity
    db.commit()
    return serialize_cart(load_cart(db, user.id))


@router.delete("/{item_id}")
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cart = get_or_create_cart(db, user.id)
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    db.delete(item)
    db.commit()
    return serialize_cart(load_cart(db, user.id))
