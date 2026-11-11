"""Cart JSON API. M6: the cart is the user's cart_items rows, always on the user's shard."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.auth import CurrentUser, get_current_user
from app.models import CartItem, Product

router = APIRouter(prefix="/api/cart", tags=["cart"])


class AddCartItemRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1)


def load_cart(db: Session, user_id) -> list[CartItem]:
    return (
        db.query(CartItem)
        .options(joinedload(CartItem.product))
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.product_id)
        .all()
    )


def _money(value) -> float:
    return float(Decimal(str(value)))


def serialize_cart(user_id, items: list[CartItem]) -> dict:
    out = []
    total = Decimal("0")
    for item in items:
        price = Decimal(str(item.product.price))
        line = price * item.quantity
        total += line
        out.append(
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "name": item.product.name,
                "price": _money(price),
                "quantity": item.quantity,
                "stock": item.product.stock,
                "line_total": _money(line),
            }
        )
    return {"cart_id": str(user_id), "items": out, "total": _money(total)}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_cart(body: AddCartItemRequest, user: CurrentUser = Depends(get_current_user)):
    db = user.db
    product = db.get(Product, body.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    if product.stock is not None and body.quantity > product.stock:
        raise HTTPException(status_code=400, detail="Not enough stock.")

    item = (
        db.query(CartItem)
        .filter(CartItem.user_id == user.id, CartItem.product_id == body.product_id)
        .first()
    )
    if item:
        new_qty = item.quantity + body.quantity
        if product.stock is not None and new_qty > product.stock:
            raise HTTPException(status_code=400, detail="Not enough stock.")
        item.quantity = new_qty
    else:
        db.add(CartItem(user_id=user.id, product_id=body.product_id, quantity=body.quantity))

    db.commit()
    return serialize_cart(user.id, load_cart(db, user.id))


@router.get("")
def get_cart(user: CurrentUser = Depends(get_current_user)):
    return serialize_cart(user.id, load_cart(user.db, user.id))


def _own_item(db: Session, user_id, item_id: uuid.UUID) -> CartItem:
    # user_id in the WHERE: a row of another user can never be touched.
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    return item


@router.put("/{item_id}")
def update_cart_item(
    item_id: uuid.UUID, body: UpdateCartItemRequest, user: CurrentUser = Depends(get_current_user)
):
    db = user.db
    item = _own_item(db, user.id, item_id)
    if item.product.stock is not None and body.quantity > item.product.stock:
        raise HTTPException(status_code=400, detail="Not enough stock.")
    item.quantity = body.quantity
    db.commit()
    return serialize_cart(user.id, load_cart(db, user.id))


@router.delete("/{item_id}")
def remove_cart_item(item_id: uuid.UUID, user: CurrentUser = Depends(get_current_user)):
    db = user.db
    db.delete(_own_item(db, user.id, item_id))
    db.commit()
    return serialize_cart(user.id, load_cart(db, user.id))
