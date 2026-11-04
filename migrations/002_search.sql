-- M5 full-text search. Run in Supabase SQL Editor.

DROP SCHEMA IF EXISTS search CASCADE;
CREATE SCHEMA search;

-- Search view
CREATE MATERIALIZED VIEW search.product_search AS
SELECT p.id,
       p.name,
       p.category,
       p.platform,
       p.description,
       p.price::numeric AS price,
       p.stock,
       setweight(to_tsvector('english', coalesce(p.name, '')), 'A') ||
       setweight(to_tsvector('english',
           coalesce(p.category, '') || ' ' ||
           coalesce(p.platform, '') || ' ' ||
           coalesce(c.names, '')), 'B') ||
       setweight(to_tsvector('english', coalesce(p.description, '')), 'C') AS fts
FROM products p
LEFT JOIN (
    SELECT pc.product_id, string_agg(cat.name, ' ') AS names
    FROM product_categories pc
    JOIN categories cat ON cat.id = pc.category_id
    GROUP BY pc.product_id
) c ON c.product_id = p.id;

-- Indexes (unique id needed for refresh concurrently)
CREATE UNIQUE INDEX product_search_id ON search.product_search (id);
CREATE INDEX product_search_fts ON search.product_search USING gin (fts);
CREATE INDEX product_search_category ON search.product_search (category);

-- Search function
CREATE OR REPLACE FUNCTION search.search_products(
    q text,
    cat text DEFAULT NULL,
    max_price numeric DEFAULT NULL,
    in_stock boolean DEFAULT NULL,
    lim int DEFAULT 20,
    off int DEFAULT 0)
RETURNS TABLE (id int, name text, category text, platform text, description text,
               price numeric, stock int, rank real, total bigint)
LANGUAGE sql STABLE AS $$
    SELECT s.id, s.name::text, s.category::text, s.platform::text, s.description::text, s.price, s.stock,
           ts_rank(s.fts, websearch_to_tsquery('english', q)) AS rank,
           count(*) OVER () AS total
    FROM search.product_search s
    WHERE s.fts @@ websearch_to_tsquery('english', q)
      AND (cat IS NULL OR s.category = cat)
      AND (max_price IS NULL OR s.price <= max_price)
      AND (in_stock IS NULL OR NOT in_stock OR s.stock > 0)
    ORDER BY rank DESC, s.id
    LIMIT least(lim, 50) OFFSET off;
$$;

-- Refresh every 5 min (needs pg_cron)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('refresh-product-search', '*/5 * * * *',
--     $$REFRESH MATERIALIZED VIEW CONCURRENTLY search.product_search$$);
-- REFRESH MATERIALIZED VIEW CONCURRENTLY search.product_search;

-- Hide search schema from the Supabase API
REVOKE ALL ON SCHEMA search FROM anon, authenticated;
