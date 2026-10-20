import unittest
from datetime import datetime

from fastapi import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Product
from app.routers.products import list_products, search_products
# Register cart/order mappings, as in the running application.
from app.routers import cart, orders


class ProductPaginationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        for i in range(1, 16):
            self.db.add(Product(id=i, name=f"Game {i}", price=10, stock=1,
                                category="Adventure" if i % 2 else "Puzzle",
                                created_at=datetime(2026, 1, 1)))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def listing(self, page, size):
        response = Response()
        items = list_products(response=response, db=self.db, current_user=None,
                              page=page, page_size=size)
        return items, response.headers

    def searching(self, query, page, size):
        response = Response()
        items = search_products(response=response, q=query, db=self.db,
                                current_user=None, page=page, page_size=size)
        return items, response.headers

    def test_pages_have_stable_order_without_overlap(self):
        first, headers = self.listing(1, 6)
        second, _ = self.listing(2, 6)
        last, _ = self.listing(3, 6)
        self.assertEqual([p.id for p in first + second + last], list(range(15, 0, -1)))
        self.assertEqual(headers["X-Total-Count"], "15")
        self.assertEqual(headers["X-Total-Pages"], "3")

    def test_search_paginates_only_matching_products(self):
        first, headers = self.searching("ADVENTURE", 1, 6)
        last, _ = self.searching("ADVENTURE", 2, 6)
        self.assertEqual([p.id for p in first + last], list(range(15, 0, -2)))
        self.assertEqual(headers["X-Total-Count"], "8")
        self.assertEqual(headers["X-Total-Pages"], "2")

    def test_page_size_and_out_of_range_page(self):
        items, headers = self.listing(99, 12)
        self.assertEqual(len(items), 3)
        self.assertEqual(headers["X-Page"], "2")
        items, headers = self.listing(1, 24)
        self.assertEqual(len(items), 15)
        self.assertEqual(headers["X-Total-Pages"], "1")

    def test_empty_search(self):
        items, headers = self.searching("not found", 8, 6)
        self.assertEqual(items, [])
        self.assertEqual(headers["X-Total-Count"], "0")
        self.assertEqual(headers["X-Page"], "1")

    def test_existing_unpaginated_requests_still_return_full_list(self):
        items, _ = self.listing(None, 6)
        self.assertEqual(len(items), 15)
        items, _ = self.searching("Puzzle", None, 6)
        self.assertEqual(len(items), 7)


if __name__ == "__main__":
    unittest.main()
