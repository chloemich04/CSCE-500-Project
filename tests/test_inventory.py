import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Product, User
from app.routers.cart import Cart, CartItem, load_cart
from app.routers.orders import Order, checkout


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine("sqlite:///" + str(Path(self.tmp.name) / "test.db"))
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        with self.sessions() as db:
            db.add_all([User(id=i, email=f"{i}@example.com", password_hash="unused",
                             account_type="customer") for i in (1, 2)])
            db.add(Product(id=1, name="Last item", price=10, stock=1))
            db.flush()
            for i in (1, 2):
                db.add(Cart(id=i, user_id=i))
                db.flush()
                db.add(CartItem(cart_id=i, product_id=1, quantity=1))
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
                user = db.get(User, user_id)
                try:
                    checkout(db, user)
                    return 201
                except HTTPException as exc:
                    return exc.status_code

        with patch("app.routers.orders.load_cart", side_effect=overlapping_load):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(buy, (1, 2)))
        self.assertEqual(sorted(results), [201, 409])
        with self.sessions() as db:
            self.assertEqual(db.get(Product, 1).stock, 0)
            self.assertEqual(db.query(Order).count(), 1)
            self.assertEqual(db.query(CartItem).count(), 1)

    def test_later_stock_failure_rolls_back_entire_order(self):
        with self.sessions() as db:
            db.add(Product(id=2, name="Sold out", price=20, stock=0))
            db.flush()
            db.add(CartItem(cart_id=1, product_id=2, quantity=1))
            db.commit()
            with self.assertRaises(HTTPException) as error:
                checkout(db, db.get(User, 1))
            self.assertEqual(error.exception.status_code, 409)
            self.assertEqual(db.get(Product, 1).stock, 1)
            self.assertEqual(db.query(Order).count(), 0)
            self.assertEqual(db.query(CartItem).filter_by(cart_id=1).count(), 2)

    def test_database_rejects_negative_stock(self):
        with self.sessions() as db:
            db.get(Product, 1).stock = -1
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()
            self.assertEqual(db.get(Product, 1).stock, 1)


if __name__ == "__main__":
    unittest.main()
