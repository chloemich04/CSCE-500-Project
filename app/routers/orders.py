"""Order JSON API: checkout from cart (no real payment) and order history.

M6: checkout is ONE local transaction on the user's shard. On Postgres it calls the
stored procedure checkout(p_user) (M6/sql/01_shard_schema.sql); on SQLite (tests) the
same steps run through the ORM in place_order().
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, joinedload

from app.auth import CurrentUser, get_current_user
from app.models import CartItem, Order, OrderItem, Product
from app.routers.cart import _money, load_cart

router = APIRouter(prefix="/api/orders", tags=["orders"])


def serialize_order(order: Order) -> dict:
    items = []
    for item in order.items:
        items.append(
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "name": item.product.name if item.product else None,
                "quantity": item.quantity,
                "price_at_order": _money(item.price_at_order),
                "line_total": _money(Decimal(str(item.price_at_order)) * item.quantity),
            }
        )
    return {
        "id": str(order.id),
        "total": _money(order.total),
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": items,
    }


def place_order(db: Session, user_id):
    """ORM version of checkout(p_user): same steps, same single transaction."""
    cart_items = load_cart(db, user_id)
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty.")
    try:
        total = Decimal("0")
        order = Order(user_id=user_id, total=Decimal("0"), status="placed")
        db.add(order)
        db.flush()
        # Stable product order (load_cart sorts by product_id) avoids deadlocks.
        for cart_item in cart_items:
            product = cart_item.product
            # Check and decrement in ONE statement; this shard's stock allocation only.
            reserved = db.execute(
                update(Product)
                .where(Product.id == product.id, Product.stock >= cart_item.quantity)
                .values(stock=Product.stock - cart_item.quantity)
                .execution_options(synchronize_session=False)
            )
            if reserved.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail=f"'{product.name}' is out of stock or has insufficient stock. Please update your cart.",
                )
            price = Decimal(str(product.price))
            db.add(OrderItem(user_id=user_id, order_id=order.id, product_id=product.id,
                             quantity=cart_item.quantity, price_at_order=price))
            total += price * cart_item.quantity
            db.delete(cart_item)
        order.total = total
        db.commit()
    except Exception:
        db.rollback()
        raise
    return order.id


def _checkout_procedure(db: Session, user_id):
    try:
        order_id = db.execute(text("SELECT checkout(:u)"), {"u": user_id}).scalar_one()
        db.commit()
        return order_id
    except DBAPIError as exc:
        db.rollback()
        msg = getattr(getattr(exc.orig, "diag", None), "message_primary", "") or str(exc.orig)
        if msg.startswith("cart is empty"):
            raise HTTPException(status_code=400, detail="Cart is empty.")
        if msg.startswith("out of stock"):
            raise HTTPException(status_code=409, detail=msg + ". Please update your cart.")
        raise


@router.post("", status_code=status.HTTP_201_CREATED)
def checkout(user: CurrentUser = Depends(get_current_user)):
    db = user.db
    if db.get_bind().dialect.name == "postgresql":
        order_id = _checkout_procedure(db, user.id)
    else:
        order_id = place_order(db, user.id)
    return serialize_order(_load_order(db, user.id, order_id))


def _load_order(db: Session, user_id, order_id) -> Order:
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.user_id == user_id, Order.id == order_id)
        .first()
    )


@router.get("")
def list_orders(user: CurrentUser = Depends(get_current_user)):
    orders = (
        user.db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return {"orders": [serialize_order(order) for order in orders]}


_ = CartItem  # imported for type clarity in place_order's cart rows
