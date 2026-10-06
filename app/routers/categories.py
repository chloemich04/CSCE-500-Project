"""Category API: many-to-many with products.

Covers M4 query cases:
- GET /api/categories/{id}           → 1 table, 1 row
- GET /api/categories/{id}/products  → JOIN products + product_categories (2 tables)
GET /api/orders already joins 3+ tables (orders, order_items, products).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Product, User, product_categories
from app.routers.products import require_manager
from app.schemas import AssignCategoriesRequest, CategoryCreate, CategoryOut, ProductOut

router = APIRouter(prefix="/api", tags=["categories"])


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(require_manager),
):
    name = payload.name.strip()
    existing = db.query(Category).filter(Category.name == name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Category already exists.")
    category = Category(name=name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Query a single table (categories) and return one row."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@router.get("/categories/{category_id}/products", response_model=list[ProductOut])
def list_products_in_category(category_id: int, db: Session = Depends(get_db)):
    """JOIN products and product_categories (2 tables)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")

    return (
        db.query(Product)
        .join(product_categories, Product.id == product_categories.c.product_id)
        .filter(product_categories.c.category_id == category_id)
        .order_by(Product.created_at.desc())
        .all()
    )


@router.put("/products/{product_id}/categories", response_model=list[CategoryOut])
def assign_product_categories(
    product_id: int,
    payload: AssignCategoriesRequest,
    db: Session = Depends(get_db),
    manager: User = Depends(require_manager),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")

    if not payload.category_ids:
        product.categories = []
        db.commit()
        return []

    categories = db.query(Category).filter(Category.id.in_(payload.category_ids)).all()
    found_ids = {c.id for c in categories}
    missing = [cid for cid in payload.category_ids if cid not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown category ids: {missing}")

    product.categories = categories
    db.commit()
    return categories
