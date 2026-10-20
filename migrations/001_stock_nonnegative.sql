-- Run once in Supabase SQL Editor for an existing database.
-- First review existing invalid inventory (do not silently change stock counts):
SELECT id, name, stock FROM products WHERE stock < 0 OR stock IS NULL;

-- Correct any rows returned above to verified inventory counts, then run:
BEGIN;
ALTER TABLE products ALTER COLUMN stock SET NOT NULL;
ALTER TABLE products ADD CONSTRAINT products_stock_nonnegative CHECK (stock >= 0);
COMMIT;
