# M5 - Search

Mini Shop (CSCE 553) - https://github.com/chloemich04/CSCE-500-Project

Our old search was just a LIKE '%word%' on the products table, so it read all 5000 products every time and didn't rank anything. We replaced it with Postgres full-text search following the recipe.

## What we did

You can search by product name, category, platform and description, and filter by category, max price and in stock. A match in the name counts more than a match in the description.

- New migration (migrations/002_search.sql): a materialized view with the products and their categories already joined, a tsvector column for the text, a GIN index on it, and one SQL function that does the search, the filters and the ranking.
- New endpoint GET /api/search (q, category, max_price, in_stock, page, page_size). It returns the results, the total and the count per category. q is max 200 chars and page_size max 50.
- The search box on the products page now uses it, and you can click a category to narrow the results.
- The view doesn't update by itself: we refresh it by hand for now. The pg_cron job to do it every 5 min is in the migration but we didn't turn it on yet.

## Checking it works

We ran a few searches where we already knew the answer (M5/search_checks.sql):

| Search | Results |
|--------|---------|
| zzzqx | 0 |
| "azure table" | 1 |
| azure | 42 |
| blue | 118 |
| house / house -blue | 69 / 68 |
| houses | 69, same as house |
| game | 3225 (the "Games" category from the many-to-many counts too) |
| game, Games, under $20 | 322 |

EXPLAIN on "azure" shows Bitmap Index Scan on product_search_fts in 0.11 ms. The old LIKE search on the same word does a Seq Scan in 16.8 ms.

## Load test

Same setup as M4: k6 locally, 8 VUs for 60 s, app on our machine talking to Supabase. Script is M5/M5-test.js. 1381 requests, none failed.

| Request | Results | p50 | p95 | DB time |
|---------|---------|-----|-----|---------|
| zzzqx | 0 | 308 ms | 749 ms | 0.05 ms |
| "azure table" | 1 | 309 ms | 722 ms | 0.10 ms |
| azure | 42 | 311 ms | 328 ms | 0.19 ms |
| blue | 118 | 312 ms | 325 ms | 0.31 ms |
| game | 3225 | 319 ms | 355 ms | 4.9 ms |
| game + filters | 322 | 315 ms | 334 ms | |
| game, page 30 | | 322 ms | 386 ms | 5.1 ms |
| old LIKE, "azure table" | 1 | 422 ms | 447 ms | 14.9 ms |
| old LIKE, game | | 421 ms | 452 ms | 14.7 ms |
| /api/products page 1 (no search) | 20 | 395 ms | 416 ms | |

DB time is from EXPLAIN ANALYZE, so it's only the time inside Postgres. The high p95 on the first two rows comes from a few slow requests at the start of the run.
