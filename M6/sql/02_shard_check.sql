-- M6 · Parts B / C: run on each shard with ITS bucket range (fail loudly).
-- shard_0: :lo = 0,  :hi = 31
-- shard_1: :lo = 32, :hi = 63
-- (setup_shards.py substitutes {lo} and {hi}; the "single" baseline gets 0..63.)
ALTER TABLE users ADD CONSTRAINT users_belong_here
  CHECK (shard_bucket(id) BETWEEN {lo} AND {hi});
