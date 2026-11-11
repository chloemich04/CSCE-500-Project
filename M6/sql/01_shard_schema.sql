-- M6 · Part A (adapted from the handout sharding_setup.sql): run on EVERY shard.
-- Run inside the target schema (setup_shards.py does: CREATE SCHEMA x; SET search_path TO x, public).
-- Differences with the handout: our column names (password_hash, total, price_at_order),
-- products keep category/platform/stock, categories + product_categories are copied too,
-- checkout() also decrements this shard's stock allocation.

-- 1. The bucket rule: identical on every database (same as shard_bucket() in app/database.py)
CREATE OR REPLACE FUNCTION shard_bucket(u uuid)
RETURNS int LANGUAGE sql IMMUTABLE AS $$
  SELECT (('x' || substr(md5(u::text), 1, 8))::bit(32)::bigint % 64)::int
$$;

-- 2. Catalog: full copy on every shard, same ids everywhere
CREATE TABLE products (
  id          uuid PRIMARY KEY,
  name        text NOT NULL,
  description text,
  category    text,
  platform    text,
  price       numeric(10,2) NOT NULL,
  stock       int  NOT NULL DEFAULT 0 CONSTRAINT products_stock_nonnegative CHECK (stock >= 0),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE categories (
  id   uuid PRIMARY KEY,
  name text NOT NULL UNIQUE
);

CREATE TABLE product_categories (
  product_id  uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  category_id uuid NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  PRIMARY KEY (product_id, category_id)
);
CREATE INDEX ON product_categories (category_id);

-- 3. Customer-owned tables: same shape on every shard, different rows
CREATE TABLE users (
  id            uuid PRIMARY KEY,
  email         text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  account_type  text NOT NULL DEFAULT 'customer'
                CHECK (account_type IN ('customer', 'store_manager')),
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cart_items (           -- no carts table: the cart = the user's rows
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id),
  product_id uuid NOT NULL REFERENCES products(id),
  quantity   int  NOT NULL CHECK (quantity > 0),
  UNIQUE (user_id, product_id)
);

CREATE TABLE orders (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id),
  total      numeric(10,2) NOT NULL DEFAULT 0,
  status     text NOT NULL DEFAULT 'placed',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, id)
);

CREATE TABLE order_items (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        uuid NOT NULL,
  order_id       uuid NOT NULL,
  product_id     uuid NOT NULL REFERENCES products(id),
  quantity       int  NOT NULL CHECK (quantity > 0),
  price_at_order numeric(10,2) NOT NULL,
  FOREIGN KEY (user_id, order_id) REFERENCES orders(user_id, id)
);

CREATE INDEX ON orders (user_id, created_at DESC);
CREATE INDEX ON order_items (user_id, order_id);
CREATE INDEX ON order_items (order_id);

-- 4. Checkout: one local transaction on the user's shard
CREATE OR REPLACE FUNCTION checkout(p_user uuid)
RETURNS uuid LANGUAGE plpgsql
SET search_path FROM CURRENT AS $$
DECLARE
  v_order uuid := gen_random_uuid();
  v_total numeric(10,2) := 0;
  r record;
BEGIN
  PERFORM 1 FROM cart_items WHERE user_id = p_user FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'cart is empty'; END IF;

  INSERT INTO orders (id, user_id, total, status) VALUES (v_order, p_user, 0, 'placed');

  -- stable product order = no deadlock between two checkouts sharing products
  FOR r IN
    SELECT c.product_id, c.quantity, p.price, p.name
    FROM cart_items c JOIN products p ON p.id = c.product_id
    WHERE c.user_id = p_user
    ORDER BY c.product_id
  LOOP
    UPDATE products SET stock = stock - r.quantity
    WHERE id = r.product_id AND stock >= r.quantity;   -- this shard's allocation
    IF NOT FOUND THEN RAISE EXCEPTION 'out of stock: %', r.name; END IF;

    INSERT INTO order_items (user_id, order_id, product_id, quantity, price_at_order)
    VALUES (p_user, v_order, r.product_id, r.quantity, r.price);
    v_total := v_total + r.price * r.quantity;
  END LOOP;

  UPDATE orders SET total = v_total WHERE id = v_order;
  DELETE FROM cart_items WHERE user_id = p_user;
  RETURN v_order;
END $$;
