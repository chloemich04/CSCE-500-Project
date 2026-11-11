import unittest
import uuid

from app.database import _default_bucket_map, shard_bucket
from app.routers.products import stock_share


class ShardingRuleTests(unittest.TestCase):
    def test_bucket_matches_sql_rule(self):
        # Values checked against SELECT shard_bucket(uuid) on Postgres (M6/sql/01_shard_schema.sql).
        u = uuid.UUID("7b0c2f6e-3a52-4f7e-9c11-2d4e8a6b9f01")
        expected = int(__import__("hashlib").md5(str(u).encode()).hexdigest()[:8], 16) % 64
        self.assertEqual(shard_bucket(u), expected)
        self.assertTrue(all(0 <= shard_bucket(uuid.uuid4()) < 64 for _ in range(1000)))

    def test_bucket_map_two_shards_is_half_half(self):
        m = _default_bucket_map(2)
        self.assertEqual([m[b] for b in (0, 31, 32, 63)], [0, 0, 1, 1])
        self.assertEqual(sum(1 for s in m.values() if s == 0), 32)
        self.assertEqual(set(_default_bucket_map(1).values()), {0})

    def test_users_spread_evenly(self):
        m = _default_bucket_map(2)
        on_0 = sum(1 for _ in range(10000) if m[shard_bucket(uuid.uuid4())] == 0)
        self.assertTrue(4700 < on_0 < 5300)

    def test_stock_shares_add_up(self):
        for total in (0, 1, 7, 100_000):
            self.assertEqual(sum(stock_share(total, i, 2) for i in range(2)), total)


if __name__ == "__main__":
    unittest.main()
