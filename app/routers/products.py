"""Products API.

M6: the catalog is copied on every shard with the same ids. Reads go to ONE shard
(the customer's own shard, or shard_0 for anonymous pages). Manager writes are
idempotent upserts applied to EVERY shard (step 8).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, require_manager
from app.database import all_shards, get_db, new_id
from app.models import Category, Product
from app.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/api", tags=["products"])

# Re-exported for older imports (categories router).
__all__ = ["router", "require_manager", "get_current_user", "stock_share", "upsert_catalog_category"]


def stock_share(total: int, shard: int, shards: int) -> int:
    """Each shard owns a slice of the units; the slices add up to the real stock."""
    return total // shards + (1 if shard < total % shards else 0)


def upsert_catalog_category(shard_dbs: list[Session], name: str) -> uuid.UUID:
    """Same category id on every shard (looked up by name on shard_0, else a new uuid)."""
    existing = (
        shard_dbs[0].query(Category).filter(func.lower(Category.name) == name.lower()).first()
    )
    category_id = existing.id if existing else new_id()
    for db in shard_dbs:
        db.merge(Category(id=category_id, name=existing.name if existing else name))
        db.flush()
    return category_id


def _write_product(product_id: uuid.UUID, payload: ProductCreate) -> dict:
    data = payload.model_dump()
    with all_shards() as dbs:
        category_id = None
        if data.get("category") and data["category"].strip():
            category_id = upsert_catalog_category(dbs, data["category"].strip())
        for i, db in enumerate(dbs):
            product = db.merge(
                Product(id=product_id, **{**data, "stock": stock_share(data["stock"], i, len(dbs))})
            )
            db.flush()
            if category_id is not None:
                category = db.get(Category, category_id)
                if category not in product.categories:
                    product.categories.append(category)
        # Not one distributed transaction: if a commit fails halfway, re-running the
        # same upsert converges every shard to the same row (idempotent).
        for db in dbs:
            db.commit()
    return {"id": product_id, **data}


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, manager: CurrentUser = Depends(require_manager)):
    return _write_product(new_id(), payload)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID, payload: ProductUpdate, manager: CurrentUser = Depends(require_manager)
):
    if manager.db.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return _write_product(product_id, payload)


@router.get("/products/search", response_model=list[ProductOut])
def search_products(
    response: Response,
    q: str = Query(..., min_length=1),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    search_term = f"%{q.lower()}%"
    query = current_user.db.query(Product).filter(
        or_(
            func.lower(Product.name).like(search_term),
            func.lower(Product.description).like(search_term),
            func.lower(Product.category).like(search_term),
            func.lower(Product.platform).like(search_term),
        )
    )
    return paginate_products(query, response, page, page_size)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    """Query a single table (products) and return one row."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.get("/products", response_model=list[ProductOut])
def list_products(
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
):
    # Stock shown = what this customer can actually buy (their shard's allocation).
    return paginate_products(current_user.db.query(Product), response, page, page_size)


def paginate_products(query, response: Response, page: int | None, page_size: int):
    # Preserve the existing array response for API consumers without pagination.
    query = query.order_by(Product.created_at.desc(), Product.id.desc())
    if page is not None:
        total = query.order_by(None).count()
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Total-Pages"] = str(pages)
        query = query.offset((page - 1) * page_size).limit(page_size)
    return query.all()
