-- M6: M5 full-text search recreated inside the shard schema (catalog = same on every shard).
-- Same view/function as migrations/002_search.sql, with uuid ids. Run on EVERY shard
-- after the catalog is loaded (REFRESH MATERIALIZED VIEW product_search after catalog changes).

CREATE MATERIALIZED VIEW product_search AS
SELECT p.id, p.name, p.category, p.platform, p.description, p.price, p.stock,
       setweight(to_tsvector('english', coalesce(p.name, '')), 'A') ||
       setweight(to_tsvector('english',
           coalesce(p.category, '') || ' ' || coalesce(p.platform, '') || ' ' ||
           coalesce(c.names, '')), 'B') ||
       setweight(to_tsvector('english', coalesce(p.description, '')), 'C') AS fts
FROM products p
LEFT JOIN (
    SELECT pc.product_id, string_agg(cat.name, ' ') AS names
    FROM product_categories pc JOIN categories cat ON cat.id = pc.category_id
    GROUP BY pc.product_id
) c ON c.product_id = p.id;

CREATE UNIQUE INDEX ON product_search (id);
CREATE INDEX ON product_search USING gin (fts);
CREATE INDEX ON product_search (category);

CREATE OR REPLACE FUNCTION search_products(
    q text, cat text DEFAULT NULL, max_price numeric DEFAULT NULL,
    in_stock boolean DEFAULT NULL, lim int DEFAULT 20, off int DEFAULT 0)
RETURNS TABLE (id uuid, name text, category text, platform text, description text,
               price numeric, stock int, rank real, total bigint)
LANGUAGE sql STABLE
SET search_path FROM CURRENT AS $$
    SELECT s.id, s.name, s.category, s.platform, s.description, s.price, s.stock,
           ts_rank(s.fts, websearch_to_tsquery('english', q)) AS rank,
           count(*) OVER () AS total
    FROM product_search s
    WHERE s.fts @@ websearch_to_tsquery('english', q)
      AND (cat IS NULL OR s.category = cat)
      AND (max_price IS NULL OR s.price <= max_price)
      AND (in_stock IS NULL OR NOT in_stock OR s.stock > 0)
    ORDER BY rank DESC, s.id
    LIMIT least(lim, 50) OFFSET off;
$$;
