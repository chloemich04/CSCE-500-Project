-- M5 checks, run after migrations/002_search.sql

SELECT count(*) AS rows, count(fts) AS with_fts FROM search.product_search;

SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'search';

SELECT 'zzzqx' AS q, count(*) FROM search.search_products('zzzqx', lim => 50)
UNION ALL SELECT '"azure table"', count(*) FROM search.search_products('"azure table"', lim => 50)
UNION ALL SELECT 'azure',         max(total) FROM search.search_products('azure')
UNION ALL SELECT 'house -blue',   max(total) FROM search.search_products('house -blue')
UNION ALL SELECT 'houses',        max(total) FROM search.search_products('houses')
UNION ALL SELECT 'game',          max(total) FROM search.search_products('game');

SELECT id, name, category, price, rank, total
FROM search.search_products('house', cat => 'Games', max_price => 20, lim => 5);

-- facets
SELECT category, count(*) AS n
FROM search.product_search
WHERE fts @@ websearch_to_tsquery('english', 'game')
GROUP BY category ORDER BY n DESC;

-- should use product_search_fts
EXPLAIN ANALYZE
SELECT id FROM search.product_search
WHERE fts @@ websearch_to_tsquery('english', 'azure');

-- old ILIKE search
EXPLAIN ANALYZE
SELECT id FROM products
WHERE lower(name) LIKE '%azure%' OR lower(description) LIKE '%azure%'
   OR lower(category) LIKE '%azure%' OR lower(platform) LIKE '%azure%';
