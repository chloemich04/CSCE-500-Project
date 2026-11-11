"""M6 · steps 3-8: build the shards and migrate the existing (M4) data into them.

    python M6/setup_shards.py sharded   # schema "shard" on DATABASE_URL (shard_0) + SHARD_1_URL (shard_1)
    python M6/setup_shards.py single    # schema "single" on DATABASE_URL: the 1-database baseline

Source = the pre-M6 tables in public (int ids) of DATABASE_URL. Every int id becomes a
deterministic uuid5, so the same product gets the same uuid on every shard. Each user
(and their orders / order_items) is written ONLY to the shard its bucket maps to; the
catalog is copied everywhere; the directory + bucket_map go to shard_0.
Destructive for the target schema only (DROP SCHEMA <schema> CASCADE); public is read-only.
"""

import hashlib
import sys
import time
import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import dotenv_values

psycopg2.extras.register_uuid()
ROOT = Path(__file__).resolve().parent
ENV = dotenv_values(ROOT.parent / ".env")
NS = uuid.UUID("6a1f6f2e-6d36-4f5e-9a55-0f6c0e2d5b10")
LOAD_TEST_STOCK = 100_000  # units per product (split over shards) so the load test never runs dry


def uid(table: str, old_id) -> uuid.UUID:
    return uuid.uuid5(NS, f"{table}:{old_id}")


def bucket(u: uuid.UUID) -> int:
    return int(hashlib.md5(str(u).encode()).hexdigest()[:8], 16) % 64


def sql(name: str, **subs) -> str:
    text = (ROOT / "sql" / name).read_text(encoding="utf-8")
    for k, v in subs.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def insert(cur, table, cols, rows):
    if rows:
        psycopg2.extras.execute_values(
            cur, f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s", rows, page_size=5000
        )


def main(mode: str):
    if mode == "sharded":
        schema, targets = "shard", [ENV["DATABASE_URL"], ENV["SHARD_1_URL"]]
    elif mode == "single":
        schema, targets = "single", [ENV["DATABASE_URL"]]
    else:
        sys.exit("usage: setup_shards.py sharded|single")
    n = len(targets)
    per = 64 // n

    # ---- read the source (pre-M6, int ids) ----
    src = psycopg2.connect(ENV["DATABASE_URL"])
    s = src.cursor()
    s.execute("SELECT id, name, description, category, platform, price, created_at, updated_at FROM public.products")
    products = s.fetchall()
    s.execute("SELECT id, name FROM public.categories")
    categories = s.fetchall()
    s.execute("SELECT product_id, category_id FROM public.product_categories")
    prod_cats = s.fetchall()
    s.execute("SELECT id, lower(email), password_hash, account_type, created_at FROM public.users")
    users = s.fetchall()
    s.execute("SELECT id, user_id, total, status, created_at FROM public.orders")
    orders = s.fetchall()
    s.execute("SELECT id, order_id, product_id, quantity, price_at_order FROM public.order_items")
    order_items = s.fetchall()
    src.close()
    print(f"source: {len(users)} users, {len(products)} products, {len(orders)} orders, {len(order_items)} order_items")

    user_uuid = {u[0]: uid("users", u[0]) for u in users}
    shard_of_user = {old: bucket(new) // per for old, new in user_uuid.items()}
    order_owner = {o[0]: o[1] for o in orders}

    for i, url in enumerate(targets):
        t0 = time.time()
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE; CREATE SCHEMA {schema};")
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute(sql("01_shard_schema.sql"))
        cur.execute(sql("02_shard_check.sql", lo=i * per, hi=i * per + per - 1))
        if i == 0:
            cur.execute(sql("03_directory.sql", shards=n))

        # catalog: same rows everywhere, stock = this shard's allocation
        share = LOAD_TEST_STOCK // n
        insert(cur, "products", ["id", "name", "description", "category", "platform", "price",
                                 "stock", "created_at", "updated_at"],
               [(uid("products", p[0]), p[1], p[2], p[3], p[4], p[5], share, p[6], p[7]) for p in products])
        insert(cur, "categories", ["id", "name"], [(uid("categories", c[0]), c[1]) for c in categories])
        insert(cur, "product_categories", ["product_id", "category_id"],
               [(uid("products", p), uid("categories", c)) for p, c in prod_cats])

        # customer-owned rows: only this shard's users
        insert(cur, "users", ["id", "email", "password_hash", "account_type", "created_at"],
               [(user_uuid[u[0]], u[1], u[2], u[3], u[4]) for u in users if shard_of_user[u[0]] == i])
        insert(cur, "orders", ["id", "user_id", "total", "status", "created_at"],
               [(uid("orders", o[0]), user_uuid[o[1]], o[2], o[3], o[4])
                for o in orders if shard_of_user[o[1]] == i])
        insert(cur, "order_items", ["id", "user_id", "order_id", "product_id", "quantity", "price_at_order"],
               [(uid("order_items", it[0]), user_uuid[order_owner[it[1]]], uid("orders", it[1]),
                 uid("products", it[2]), it[3], it[4])
                for it in order_items if shard_of_user[order_owner[it[1]]] == i])
        if i == 0:
            insert(cur, "user_directory", ["email", "user_id"], [(u[1], user_uuid[u[0]]) for u in users])

        cur.execute(sql("04_search.sql"))
        conn.commit()
        conn.autocommit = True
        cur.execute("ANALYZE")
        cur.execute("SELECT count(*) FROM users")
        print(f"shard_{i} ({schema}): {cur.fetchone()[0]} users loaded in {time.time() - t0:.1f}s")
        conn.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
