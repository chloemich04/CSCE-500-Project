"""M6 · slide 41 checks: users split evenly, 0 rows on the wrong shard, a wrong insert is
refused, the catalog is identical everywhere, Python bucket == SQL bucket."""
import sys, uuid
from pathlib import Path
import psycopg2, psycopg2.extras
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import shard_bucket  # noqa: E402

psycopg2.extras.register_uuid()
ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
shards = [(0, 31, ENV["DATABASE_URL"]), (32, 63, ENV["SHARD_1_URL"])]

for i, (lo, hi, url) in enumerate(shards):
    c = psycopg2.connect(url); cur = c.cursor(); cur.execute("SET search_path TO shard, public")
    q = lambda s, *a: (cur.execute(s, a), cur.fetchone())[1]
    print(f"--- shard_{i} (buckets {lo}-{hi})")
    print("users / orders / order_items:", q("SELECT count(*) FROM users")[0], q("SELECT count(*) FROM orders")[0], q("SELECT count(*) FROM order_items")[0])
    print("users on the wrong shard (expect 0):", q("SELECT count(*) FROM users WHERE shard_bucket(id) NOT BETWEEN %s AND %s", lo, hi)[0])
    print("orders whose user is not here (expect 0):", q("SELECT count(*) FROM orders o LEFT JOIN users u ON u.id = o.user_id WHERE u.id IS NULL")[0])
    print("catalog count(*), sum(price), sum(stock):", q("SELECT count(*), sum(price), sum(stock) FROM products"))
    for _ in range(3):
        u = uuid.uuid4()
        assert q("SELECT shard_bucket(%s)", u)[0] == shard_bucket(u), "bucket mismatch"
    print("python bucket == SQL bucket on random uuids: OK")
    # a user that belongs to the OTHER shard must be refused
    while True:
        u = uuid.uuid4()
        if not (lo <= shard_bucket(u) <= hi): break
    try:
        cur.execute("INSERT INTO users (id, email, password_hash) VALUES (%s, 'wrong@x.com', 'x')", (u,))
        print("!!! wrong-shard insert ACCEPTED")
    except psycopg2.errors.CheckViolation as e:
        print("wrong-shard insert refused:", e.diag.message_primary)
    c.rollback(); cur.execute("SET search_path TO shard, public")
    if i == 0:
        cur.execute("""SELECT m.shard, count(*) FROM user_directory d
                       JOIN bucket_map m ON m.bucket = shard_bucket(d.user_id) GROUP BY m.shard ORDER BY 1""")
        print("directory -> shard split:", cur.fetchall())
    c.close()
