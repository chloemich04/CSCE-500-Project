"""Order JSON API: checkout from cart (no real payment) and order history."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Session, joinedload, relationship

from app.database import Base, get_db
from app.models import User
from app.routers.cart import Product, get_current_user, load_cart, _money

# Product is imported so SQLAlchemy can resolve OrderItem.product.
_ = Product

router = APIRouter(prefix="/api/orders", tags=["orders"])


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total = Column(Numeric, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_at_order = Column(Numeric, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


def serialize_order(order: Order) -> dict:
    items = []
    for item in order.items:
        items.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.product.name if item.product else None,
                "quantity": item.quantity,
                "price_at_order": _money(item.price_at_order),
                "line_total": _money(Decimal(str(item.price_at_order)) * item.quantity),
            }
        )
    return {
        "id": order.id,
        "total": _money(order.total),
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": items,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def checkout(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = load_cart(db, user.id)
    cart_items = list(cart.items)
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    total = Decimal("0")
    order = Order(user_id=user.id, total=Decimal("0"), status="placed")
    db.add(order)
    db.flush()

    for cart_item in cart_items:
        product = cart_item.product
        if product is None:
            raise HTTPException(status_code=400, detail="A cart item refers to a missing product.")
        if product.stock is not None and cart_item.quantity > product.stock:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for '{product.name}'.",
            )

        price = Decimal(str(product.price))
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                price_at_order=price,
            )
        )
        total += price * cart_item.quantity
        if product.stock is not None:
            product.stock -= cart_item.quantity

        db.delete(cart_item)

    order.total = total
    db.commit()
    return serialize_order(_load_order(db, order.id))


def _load_order(db: Session, order_id: int) -> Order:
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )


@router.get("")
def list_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    orders = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return {"orders": [serialize_order(order) for order in orders]}
