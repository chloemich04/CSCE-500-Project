-- Mini Shop — seed categories + product_categories (with skew)
-- Run in: Supabase Dashboard → SQL Editor → New query → Run
-- Safe to re-run: all inserts use ON CONFLICT DO NOTHING.

-- ---------------------------------------------------------------------------
-- 1. Fill `categories`
--    - 8 standard names
--    - plus distinct non-empty values from products.category
-- ---------------------------------------------------------------------------
INSERT INTO categories (name) VALUES
    ('Electronics'),
    ('Books'),
    ('Home'),
    ('Toys'),
    ('Sports'),
    ('Clothing'),
    ('Beauty'),
    ('Games')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name)
SELECT DISTINCT btrim(p.category)
FROM products p
WHERE p.category IS NOT NULL
  AND btrim(p.category) <> ''
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. Link each product to its existing text category (products.category)
--    Case-insensitive match on categories.name.
--    If both "games" and "Games" exist, prefer the standard 8 names.
-- ---------------------------------------------------------------------------
INSERT INTO product_categories (product_id, category_id)
SELECT DISTINCT ON (p.id, lower(btrim(p.category)))
    p.id,
    c.id
FROM products p
JOIN categories c
  ON lower(c.name) = lower(btrim(p.category))
WHERE p.category IS NOT NULL
  AND btrim(p.category) <> ''
ORDER BY
    p.id,
    lower(btrim(p.category)),
    CASE
        WHEN c.name IN (
            'Electronics', 'Books', 'Home', 'Toys',
            'Sports', 'Clothing', 'Beauty', 'Games'
        ) THEN 0
        ELSE 1
    END,
    c.id
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. Extra many-to-many links with marked SKEW
--    Independent random draws (a product can land in more than one of these).
--    ~60% Games, ~30% Electronics, ~15% Home
-- ---------------------------------------------------------------------------
INSERT INTO product_categories (product_id, category_id)
SELECT p.id, c.id
FROM products p
CROSS JOIN categories c
WHERE c.name = 'Games'
  AND random() < 0.60
ON CONFLICT DO NOTHING;

INSERT INTO product_categories (product_id, category_id)
SELECT p.id, c.id
FROM products p
CROSS JOIN categories c
WHERE c.name = 'Electronics'
  AND random() < 0.30
ON CONFLICT DO NOTHING;

INSERT INTO product_categories (product_id, category_id)
SELECT p.id, c.id
FROM products p
CROSS JOIN categories c
WHERE c.name = 'Home'
  AND random() < 0.15
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Verification: product count per category (desc)
-- ---------------------------------------------------------------------------
SELECT
    c.id,
    c.name,
    COUNT(pc.product_id) AS product_count
FROM categories c
LEFT JOIN product_categories pc ON pc.category_id = c.id
GROUP BY c.id, c.name
ORDER BY product_count DESC, c.name;
