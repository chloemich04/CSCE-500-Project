from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Product, User
from app.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/api", tags=["products"])


def get_current_user(
    db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None, alias="Authorization")
):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authentication scheme.")

    from jose import jwt

    from app.config import settings

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    return user


def require_manager(user: User = Depends(get_current_user)):
    if user.account_type != "store_manager":
        raise HTTPException(status_code=403, detail="Store manager access required.")
    return user


def sync_named_category(db: Session, product: Product) -> None:
    """If products.category (text) is set, also link that name in the M2M table."""
    if not product.category or not product.category.strip():
        return
    name = product.category.strip()
    category = db.query(Category).filter(func.lower(Category.name) == name.lower()).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    if category not in product.categories:
        product.categories.append(category)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(require_manager),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()
    sync_named_category(db, product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    manager: User = Depends(require_manager),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")

    for key, value in payload.model_dump().items():
        setattr(product, key, value)

    sync_named_category(db, product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products/search", response_model=list[ProductOut])
def search_products(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    search_term = f"%{q.lower()}%"
    return (
        db.query(Product)
        .filter(
            or_(
                func.lower(Product.name).like(search_term),
                func.lower(Product.description).like(search_term),
                func.lower(Product.category).like(search_term),
                func.lower(Product.platform).like(search_term),
            )
        )
        .order_by(Product.created_at.desc())
        .all()
    )


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Query a single table (products) and return one row."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.created_at.desc()).all()
