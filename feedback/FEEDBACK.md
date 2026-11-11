# Feedback — Mini Shop

**Relative standing in this class: A.** Read from the code on 11 November 2026.

This letter is search and sharding. Those are the two pieces that set the standing. Other notes are at the end and are separate from it.

You are the A because both are in the process a customer actually hits, and the main operations match the placement. Search is full text. A user's cart and checkout stay on that user's shard.

## Search

`GET /api/search` calls `search_products()` with a bound `websearch` query, a category, a max price, an in-stock flag, and a page. The product page uses that route whenever there is a query, and it sends `page` and `page_size`. Facets come back with the page. `M6/sql/04_search.sql` builds a GIN index on `product_search.fts`. That is the search this course is about: the predicate and the index are the same columns.

Browse with an empty query still uses `GET /api/products`. The page sends `page`, so that screen is bounded. The route itself, when `page` is omitted, returns every product. Category listings do too. Make the paged search the only catalog read, including browse and category, so a client cannot pull the table by leaving the page off.

## Sharding

This is in the serving path, which is why it counts.

- Login goes through the directory (email to user id), then the user's shard.
- The shard is recomputed from the user id. The copy of the shard inside the token is not trusted.
- Users, cart lines, and orders for one person live on one shard. Checkout is one transaction on that shard (`checkout(p_user)` on Postgres, the same steps in `place_order` on SQLite).
- The catalog is copied onto every shard with the same ids. A manager write is applied to all of them.

Stock is the part that is not finished. Catalog rows are copied. Stock is not: each shard holds a slice, and the slices add up to the real quantity. Search opens shard 0. A signed-in product list opens the customer's shard. Those two numbers are the same only while `SHARD_COUNT` is 1. With two shards, search can show units this customer cannot buy, and the other shard can be holding the rest.

A store has one quantity. Either copy stock the way you copy the catalog and decrement it on every shard in the same catalog write, or keep the split and show "available on your shard" on search, on the product list, in the cart, and at checkout. Search, the list, and `UPDATE ... WHERE stock >= quantity` have to be the same number.

## Software engineering notes

These do not change the standing.

- Registration accepts `account_type`, including `store_manager`. A new account should be a customer. Promoting a manager should be a step the customer cannot call.
- `GET /api/orders` returns every order for that user. Page it the same way as search.
- Category is still a text column and a link table. The search document and the manager form need one source, or a rename will show up in one and not the other.
