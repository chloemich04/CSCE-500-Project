# M6 Partitioning

Sabri and Chloe, November 10 2026

## What we did

We followed the 10 steps from "How to Shard in Azure + Supabase". All our ids are uuids now and every row that belongs
to a customer lives on one shard, picked from the hashed user id. Products and categories are copied on both shards.
To log in, the app first checks a small directory on shard_0 that maps each email to a user id.

We also moved our M4 data into the shards so we had real data to test with: 20,000 users, 5,000 products and 60,000
old orders.

For the load tests we kept the same code and the same data before and after. The only thing that changes is that the
first test runs on one database and the second one runs on two.

## Before sharding

Our k6 test only does writes. Every virtual user is a different customer who puts two games in their cart, changes the
quantity of one and then checks out, over and over. All the checkouts buy from the same 20 products, kind of like a
sale, so a lot of buyers end up updating the same stock rows. Each test runs for a minute.

To make writes heavier than in M5 we turned checkout into a stored procedure. One checkout now creates the order and its
items, lowers the stock and empties the cart in a single transaction.

| Users | Writes/s | p50 | p95 | p99 | Errors |
|-------|----------|-----|-----|-----|--------|
| 8 | 14.4 | 693 ms | 719 ms | 767 ms | 0 |
| 16 | 20.3 | 808 ms | 1.56 s | 2.00 s | 0 |
| 32 | 21.2 | 1.57 s | 4.06 s | 5.37 s | 0 |
| 64 | 22.4 | 1.55 s | 12.4 s | 18.2 s | 0 |

Past 16 users the throughput stops going up. We stay stuck at around 22 writes per second no matter how many users we
add. Meanwhile the p95 keeps growing until it hits 12 seconds at 64 users. The requests are just waiting in line.

We looked at pg_stat_statements to see where the time went. Checkout is by far the slowest query because the buyers all
wait on the same stock rows. But the database itself barely did any work: all the queries together took about 7
seconds of execution over the whole test. Most of the time is spent on the network. One write makes around 7 round
trips to Supabase at 76 ms each, so it holds its connection for half a second.

What actually limits us is the number of connections. We opened connections one by one and a free Supabase project
refuses the 16th. Our app uses 12 of them. If each one is busy for half a second per write that gives about 24
writes per second at most, which is close to what we measured. Adding more app workers wouldn't change anything
because Supabase would just refuse the extra connections. A second database comes with 15 more, so this is a case where
sharding should help.

## Sharding worksheet

### Step 1: our busiest writes

These numbers come from the 64 user test, scaled up to an hour.

| User action | Tables it writes to | Per hour |
|-------------|---------------------|----------|
| Add to cart | cart_items | 40,000 |
| Change a quantity | cart_items | 20,000 |
| Checkout | orders, order_items, products, cart_items | 20,000 |
| Remove from cart | cart_items | not in our test |
| Sign up | user_directory then users | rare |

### Step 2: owner and shard key

All of these writes only touch the rows of one customer, so the owner is always the customer and we used the user id as
our shard key.

It passes the three checks on the worksheet. Every request already knows the user id since it's in the login token. The
id never changes, while an email could. And because it's hashed, new users get spread over both shards instead of
piling up on one.

For this to work we added a user_id column to order_items. Cart items now point straight to the user instead of going
through a carts table.

### Step 3: hot owner

The worst case we could think of is a bot buying a new console the minute it comes out. Every checkout for that console
updates the same stock row. Instead of copying the stock on both shards we split it in half, so each shard sells its own
share of the units and two buyers on different shards lock two different rows. The downside is that one shard can say
the console is sold out while the other one still has some left.

### Step 4: pages that read across customers

Login is the only one we really have and it goes through the directory. The product list and the search only read the
catalog, which is on both shards, so they just ask shard_0. If we ever add a best-sellers page or a sales report for
the manager, it will have to ask both shards and add the results together. The email is the only thing that has to be
unique across the whole app, that's why it lives in the directory.

### Step 5: placement plan

Users, cart items, orders and order items live on the customer's shard. Products, categories and the table linking them
are copied on both shards. The directory and the bucket map are only on shard_0. We use 64 buckets: 0 to 31 go to
shard_0 and 32 to 63 go to shard_1.

## Data model before and after

Before M6 everything was in one Supabase database with integer ids. Each user had a cart with cart items. Orders had
order items that didn't know which user they belonged to. Every customer wrote to the same database and the same stock
rows.

Now we have two Supabase projects with the same tables. A customer and everything they own sits on one of them, and
each of those rows has the user id on it. We dropped the carts table since a cart is just a user's cart items. Products
and categories are identical on both sides except for the stock, which is split.

When you log in, the app finds your user id in the directory, figures out your shard and puts it in your token. Anything
you do after that only talks to your shard. When a manager adds a product, the app writes it to both shards with the
same id.

To check the migration we ran the queries from the slides. The users split 10,040 on shard_0 and 9,963 on shard_1 and
nobody is on the wrong shard. If we try to insert a user on the wrong side the check constraint refuses it. The catalog
is the same on both.

## After sharding

Same test, same users, same app settings. We just added the second database. Half of the test users ended up on each
shard.

| Users | Writes/s before | Writes/s after | p95 before | p95 after |
|-------|-----------------|----------------|------------|-----------|
| 8 | 14.4 | 18.4 | 719 ms | 714 ms |
| 16 | 20.3 | 35.6 | 1.56 s | 0.77 s |
| 32 | 21.2 | 50.0 | 4.06 s | 1.46 s |
| 64 | 22.4 | 52.8 | 12.4 s | 3.62 s |

There were no errors in any of the runs. At 64 users we went from 22 to 53 writes per second and the p95 dropped from
12 seconds to under 4.

When we split the results by shard, shard_0 on its own still maxes out at about 21 writes per second, pretty much the
same as the single database before. Each database still has the same limit. We just have two of them now so the
customers on shard_1 aren't fighting over shard_0's connections and stock rows anymore.

We expected the throughput to double but it went up 2.4 times. That's because we accidentally created shard_1 in
us-east-1 instead of us-west-2. It turns out to be closer to us, 49 ms instead of 76. Round trips are shorter there
so it handles more writes. With both shards in the same region it would probably be closer to 44 writes per second.

At 8 users sharding barely changes anything since there's no queue yet. It only starts to pay off once the database is
really the bottleneck.

## Downsides

Anything that needs data from several customers, like a sales report, now has to query both shards. Signing up writes
to two databases, the directory first and then the user's shard. If the second write fails we delete the email from the
directory, but if the server crashed right between the two we would end up with an email that has no account.

When a manager edits a product the app updates one shard and then the other, not in a single transaction. Since the id
is the same on both, running the update again fixes things if one of them fails. The split stock also means a product
can show as sold out for some customers while the other shard still has units.

We're on the free plan, which only allows two projects, so shard_0 is a separate schema inside our existing project.
Before merging into main, the Azure VM also needs the URL of the second database in its .env, otherwise the customers on
shard_1 can't log in.
