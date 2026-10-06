# M4 — Database Scaling

**Mini Shop** — our e-commerce app for video games (CSCE 553).
Repo: https://github.com/chloemich04/CSCE-500-Project

The point of M4 was to actually feel the database slow down — grow it big enough and query it in complex enough ways that the performance problems show up on their own. So we added a many-to-many relationship, made sure we had queries hitting one, two, and three-plus tables, filled the database with a lot of realistic (and deliberately lopsided) data, and load-tested each kind of query to see which ones hurt. Everything is fake data, and we ran the tests locally since the instructor said that was fine for now.

## The schema

Our app already had the usual one-to-many links. What was missing for M4 was a real many-to-many, so we added one between products and categories: a game can belong to several categories, and a category holds many games. That meant two new tables, `categories` and the join table `product_categories`.

| Relationship | Tables | Type |
|--------------|--------|------|
| A user has many orders | users → orders | one-to-many |
| An order has many items | orders → order_items | one-to-many |
| A product appears in many order lines | products → order_items | one-to-many |
| A product has many categories, a category has many products | products ↔ categories, via `product_categories` | **many-to-many** |

## The APIs we test

Between these five we cover the full spread the assignment asks for — one / two / three-plus tables, and both single results and lists.

| Endpoint | Tables | Result | Covers |
|----------|--------|--------|--------|
| `GET /api/products/{id}` | 1 (products) | single | 1 table, single |
| `GET /api/categories/{id}` | 1 (categories) | single | 1 table, single |
| `GET /api/products` | 1 (products) | list | 1 table, list |
| `GET /api/categories/{id}/products` | 2+ (categories ⋈ product_categories ⋈ products) | list | many-to-many join |
| `GET /api/orders` | 3 (orders ⋈ order_items ⋈ products) | list | 3+ table join |

## Filling the database

We used the course seed kit (`seed_store.py` at full scale) to load the database properly. The kit builds in natural skew — a few customers order a lot, a few products sell a lot — which is what makes slow queries show up on the busy rows instead of evenly.

| Table | Rows |
|-------|------|
| users | 20,000 |
| products | 5,000 |
| orders | 60,000 |
| order_items | 148,180 |
| whole database | ~33 MB |

Then we skewed the categories on purpose, piling a big chunk of products into a few of them so the sizes would be wildly uneven. That uneven split is the whole trick: it lets us run the same query on a tiny category and a huge one and watch the difference.

| Category | Products |
|----------|----------|
| Games | 3,194 |
| Electronics | 1,932 |
| Home | 1,294 |
| Sports | 664 |
| Beauty | 656 |
| Clothing | 643 |

## How we tested

| Setting | Value |
|---------|-------|
| Tool | k6 v2.2.0 (local) |
| Target | http://127.0.0.1:8000 |
| Load | 8 virtual users, 60 s |
| Auth | logs in once as a seeded user with many orders (so the order query has real work) |
| Metric | per-endpoint latency, p50 / p95 / p99 |

## Results

| Endpoint | What it does | p50 | p95 | p99 | Errors |
|----------|--------------|-----|-----|-----|--------|
| `GET /api/products/{id}` | one row, one table | 697 ms | 1.68 s | 2.32 s | 0% |
| `GET /api/categories/{id}/products` — Sports (664) | join, small category | 869 ms | 1.65 s | 2.28 s | 0% |
| `GET /api/categories/{id}/products` — Games (3,194) | join, big category | 1.00 s | 2.52 s | 3.12 s | 0% |
| `GET /api/products` (5,000 rows) | one table, big list | 1.62 s | 2.77 s | 3.14 s | 0% |
| `GET /api/orders` | three-table join | 2.90 s | 3.79 s | 4.00 s | 0% |

Everything came back clean (0% errors). The latencies are high across the board because it's one local process talking to a remote database stuffed with 148k+ rows, but the interesting part isn't the absolute numbers — it's how they compare.

The clearest result is Sports vs Games: same exact query, but the 664-product category runs around 869 ms while the 3,194-product one is up at a full second, and the gap gets worse at the tail (p99 goes from 2.28 s to 3.12 s). Same code, more data, slower — which is the whole idea behind M4.

The order history query was the slowest of all at nearly 3 seconds, which makes sense since joining three tables for a customer with a pile of orders is just more work. And listing all 5,000 products at once (1.62 s) was slower than the single-category join even though it only touches one table — so it's not only about how many tables you join, it's also about how much data you haul back. The cheapest, unsurprisingly, was fetching one product by its id. Bottom line: things slow down both with more data and with more joins, exactly what the assignment was after.

## Caveats

| Caveat | Why it matters |
|--------|----------------|
| Tests run locally | The laptop → Supabase network hop is in every number, but what we measure (size + join complexity on the DB) is the same wherever the load comes from. |
| Single local worker | Absolute latencies look big; the comparison between query types is the point, not the raw values. |
| argon2 hashes | Seeded accounts use argon2, so we had to install `argon2_cffi` for logins to work during the tests. |
