"""Product search (Postgres only, see migrations/002_search.sql)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api", tags=["search"])

SEARCH = text("""
    SELECT * FROM search.search_products(
        :q, :cat, CAST(:max_price AS numeric), CAST(:in_stock AS boolean), :lim, :off)
""")

FACETS = text("""
    SELECT category, count(*) AS n
    FROM search.product_search
    WHERE fts @@ websearch_to_tsquery('english', :q)
    GROUP BY category
    ORDER BY n DESC
""")


@router.get("/search")
def search_products(
    response: Response,
    q: str = Query(min_length=1, max_length=200),
    category: Optional[str] = None,
    max_price: Optional[float] = Query(default=None, ge=0),
    in_stock: Optional[bool] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    params = dict(
        q=q.strip(),
        cat=category,
        max_price=max_price,
        in_stock=in_stock,
        lim=page_size,
        off=(page - 1) * page_size,
    )
    rows = db.execute(SEARCH, params).mappings().all()
    facets = db.execute(FACETS, {"q": params["q"]}).mappings().all()

    total = rows[0]["total"] if rows else 0
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Total-Pages"] = str((total + page_size - 1) // page_size)

    return {
        "q": params["q"],
        "page": page,
        "page_size": page_size,
        "total": total,
        "results": [
            {k: (float(v) if k == "price" else v) for k, v in r.items() if k != "total"} for r in rows
        ],
        "facets": [dict(f) for f in facets],
    }
