"""Category API: many-to-many with products (catalog = copied on every shard).

Covers M4 query cases:
- GET /api/categories/{id}           → 1 table, 1 row
- GET /api/categories/{id}/products  → JOIN products + product_categories (2 tables)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_manager
from app.database import all_shards, get_db
from app.models import Category, Product, product_categories
from app.routers.products import upsert_catalog_category
from app.schemas import AssignCategoriesRequest, CategoryCreate, CategoryOut, ProductOut

router = APIRouter(prefix="/api", tags=["categories"])


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, manager: CurrentUser = Depends(require_manager)):
    name = payload.name.strip()
    if manager.db.query(Category).filter(Category.name == name).first() is not None:
        raise HTTPException(status_code=409, detail="Category already exists.")
    with all_shards() as dbs:
        category_id = upsert_catalog_category(dbs, name)
        for db in dbs:
            db.commit()
    return {"id": category_id, "name": name}


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/categories/{category_id}", response_model=CategoryOut)
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    """Query a single table (categories) and return one row."""
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@router.get("/categories/{category_id}/products", response_model=list[ProductOut])
def list_products_in_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    """JOIN products and product_categories (2 tables)."""
    if db.get(Category, category_id) is None:
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
    product_id: uuid.UUID,
    payload: AssignCategoriesRequest,
    manager: CurrentUser = Depends(require_manager),
):
    with all_shards() as dbs:
        result = []
        for db in dbs:
            product = db.get(Product, product_id)
            if product is None:
                raise HTTPException(status_code=404, detail="Product not found.")
            categories = (
                db.query(Category).filter(Category.id.in_(payload.category_ids)).all()
                if payload.category_ids else []
            )
            missing = set(payload.category_ids) - {c.id for c in categories}
            if missing:
                raise HTTPException(status_code=404, detail=f"Unknown category ids: {sorted(map(str, missing))}")
            product.categories = categories
            result = categories
        for db in dbs:
            db.commit()
        return [{"id": c.id, "name": c.name} for c in result]
