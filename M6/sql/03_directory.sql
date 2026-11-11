-- M6 · Part D: run on shard_0 ONLY (directory; shard_bucket already exists there).
-- Used by sign-up (claim the email) and login (email -> user_id -> shard).

CREATE TABLE user_directory (
  email   text PRIMARY KEY,            -- stored lower-cased
  user_id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid()
);

CREATE TABLE bucket_map (
  bucket int  PRIMARY KEY CHECK (bucket BETWEEN 0 AND 63),
  shard  text NOT NULL
);

-- {shards} = 2 for the sharded setup (0..31 -> shard_0, 32..63 -> shard_1),
--            1 for the single-database baseline (everything -> shard_0).
INSERT INTO bucket_map (bucket, shard)
SELECT b, 'shard_' || (b / (64 / {shards}))
FROM generate_series(0, 63) AS b;
