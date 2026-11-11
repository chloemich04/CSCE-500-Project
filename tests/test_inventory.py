import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CartItem, Order, Product, User
from app.routers.cart import load_cart
from app.routers.orders import place_order

U1, U2 = uuid.UUID(int=1), uuid.UUID(int=2)
P1, P2 = uuid.UUID(int=101), uuid.UUID(int=102)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine("sqlite:///" + str(Path(self.tmp.name) / "test.db"))
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        with self.sessions() as db:
            db.add_all([User(id=u, email=f"{u}@example.com", password_hash="unused",
                             account_type="customer") for u in (U1, U2)])
            db.add(Product(id=P1, name="Last item", price=10, stock=1))
            db.flush()
            for u in (U1, U2):
                db.add(CartItem(user_id=u, product_id=P1, quantity=1))
            db.commit()

    def tearDown(self):
        self.engine.dispose()
        self.tmp.cleanup()

    def test_two_buyers_only_one_gets_last_item(self):
        barrier = threading.Barrier(2)

        def overlapping_load(db, user_id):
            cart = load_cart(db, user_id)
            barrier.wait(timeout=10)  # Both buyers have read stock=1.
            return cart

        def buy(user_id):
            with self.sessions() as db:
                try:
                    place_order(db, user_id)
                    return 201
                except HTTPException as exc:
                    return exc.status_code

        with patch("app.routers.orders.load_cart", side_effect=overlapping_load):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(buy, (U1, U2)))
        self.assertEqual(sorted(results), [201, 409])
        with self.sessions() as db:
            self.assertEqual(db.get(Product, P1).stock, 0)
            self.assertEqual(db.query(Order).count(), 1)
            self.assertEqual(db.query(CartItem).count(), 1)

    def test_later_stock_failure_rolls_back_entire_order(self):
        with self.sessions() as db:
            db.add(Product(id=P2, name="Sold out", price=20, stock=0))
            db.flush()
            db.add(CartItem(user_id=U1, product_id=P2, quantity=1))
            db.commit()
            with self.assertRaises(HTTPException) as error:
                place_order(db, U1)
            self.assertEqual(error.exception.status_code, 409)
            self.assertEqual(db.get(Product, P1).stock, 1)
            self.assertEqual(db.query(Order).count(), 0)
            self.assertEqual(db.query(CartItem).filter_by(user_id=U1).count(), 2)

    def test_database_rejects_negative_stock(self):
        with self.sessions() as db:
            db.get(Product, P1).stock = -1
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
            self.assertEqual(db.get(Product, P1).stock, 1)


if __name__ == "__main__":
    unittest.main()
