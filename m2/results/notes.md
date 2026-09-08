# M2 Resource Notes

## Test configuration

- Git commit: `bd1072a`
- Local environment: Windows laptop
- Local API: `http://127.0.0.1:8000`
- Database: Existing Supabase PostgreSQL database
- Timezone: America/Chicago (CDT, UTC-05:00)
- API command: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- API process: `python.exe`
- API PID:10480
- Laptop connected to AC power:
- Load driver: `load_baseline.py`
- Python version: Python 3.14.7

## Dataset

- Product count: 50
- `GET /api/products` response size: 8,515 bytes
- Dataset remained unchanged during read sweep: yes

## Idle sample

- Timestamp: 2026-09-07 18:06:35 -05:00
- API CPU:0
- API working-set memory: 47,728K
- Database connection count: 15
- Database connection states: 7 state unavailable/NULL, 7 idle, 1 active
- Database measurement timestamp: 2026-09-07 18:15:20 -05:00
- Notes: The active count likely includes the Supabase SQL Editor connection.
- Screenshot filename: m2\results\local-L-idle-180635.png

## Test stages

Resource observations for each stage will be added below.

## Confounds and unusual events

- Local API communicates with Supabase over the network.
- Add token expiry, interruptions, background activity, or thermal issues here.

## L-health-c2

- Start: approximately 2026-09-07 21:54:20 -05:00, derived from total runtime
- Measurement: 10-second warmup followed by 60-second measured window
- Mid-stage resource observation: not captured
- API PID: 10920

- End timestamp: not captured; expected near 22:08:16 based on the 10-second warmup and measured duration
- Attempts: 12,084
- Successes: 12,084
- Errors: 0
- Successful RPS: 201.393
- p50: 13.64 ms
- p95: 20.53 ms
- p99: 27.14 ms
- Maximum latency: 106.01 ms
- Error rate: 0%
- Notes: Mid-stage CPU, memory, and screenshot were not captured. The control stage was retained and was not rerun.

## L-read-c4

- Start: 2026-09-07 22:30:07 -05:00
- Mid-stage timestamp: 2026-09-07 22:30:45 -05:00
- End timestamp: not captured; expected near 22:31:17
- API PID: 10920
- API CPU: 1%
- API working-set memory: 52,840 KB (approximately 51.6 MB)
- Database connections: 21 total; 13 idle, 7 inactive/unreported, 1 active
- Screenshot: `local-L-read-c4-223045.png`
- Attempts: 620
- Successes: 620
- Errors: 0
- Successful RPS: 10.283
- p50: 385.28 ms
- p95: 402.95 ms
- p99: 518.39 ms
- Maximum latency: 854.98 ms
- Error rate: 0%

## L-read-c8

- Start: 2026-09-07 22:42:01 -05:00
- Mid-stage timestamp: 2026-09-07 22:42:42 -05:00
- End: 2026-09-07 22:43:17 -05:00
- API PID: 10920
- API CPU: 1%
- API working-set memory: 59,320 KB (approximately 57.9 MB)
- Database connections: 26 total; 18 idle, 7 inactive/unreported, 1 active
- Screenshot: `local-L-read-c8-224242.png`
- Attempts: 1,226
- Successes: 1,226
- Errors: 0
- Successful RPS: 20.35
- p50: 379.43 ms
- p95: 405.71 ms
- p99: 845.95 ms
- Maximum latency: 1,235.66 ms
- Error rate: 0%

## L-read-c16

- Start: 2026-09-07 22:48:41 -05:00
- Mid-stage timestamp: 2026-09-07 22:49:23 -05:00
- End: 2026-09-07 22:50:01 -05:00
- API PID: 10920
- API CPU: 2%
- API working-set memory: 125,488 KB (approximately 122.5 MB)
- Database connections: 28 total; 11 idle, 9 idle in transaction, 7 state unavailable/NULL, 1 active
- Attempts: 1,976
- Successes: 1,976
- Errors: 0
- Successful RPS: 32.682
- p50: 467.35 ms
- p95: 595.38 ms
- p99: 770.59 ms
- Maximum latency: 914.34 ms
- Error rate: 

## L-read-c16-repeat

- Start: 2026-09-07 23:00:59 -05:00
- Mid-stage timestamp: 2026-09-07 23:01:40 -05:00
- End: 2026-09-07 23:02:14 -05:00
- Authoritative measured duration: 60.518 seconds
- API PID: 10920
- API CPU: 2%
- API working-set memory: 125,548 KB (approximately 122.6 MB)
- Database connections: 28 total; 10 idle in transaction, 10 idle, 7 state unavailable/NULL, 1 active
- Attempts: 1,983
- Successes: 1,983
- Errors: 0
- Successful RPS: 32.767
- p50: 472.77 ms
- p95: 560.95 ms
- p99: 706.88 ms
- Maximum latency: 961.95 ms
- Error rate: 0%
- Repeatability: RPS differed from the original c16 stage by approximately 0.26%.

## Invalid L-write-c16 configuration run

- Start: 2026-09-07 23:25:54 -05:00
- End: 2026-09-07 23:27:15 -05:00
- API CPU: 1%
- API working-set memory: 130,520 KB
- Database connections: 28 total; 12 idle, 8 idle in transaction, 7 state unavailable/NULL, 1 active
- Attempts: 2,452
- Successes: 0
- Errors: 2,452
- HTTP status: all responses were 422
- Cause: The initial `--body-file` implementation loaded the JSON into `body_text`, but the request still used the empty `args.body` value.
- Resolution: The driver was corrected to encode and send `body_text`.
- Treatment: This was a request-configuration error, not a capacity result. It is retained for transparency and excluded from performance tables and graphs.

## Write body diagnostic

- Label: `prep-L-write-body-check`
- Concurrency: 1
- Warmup: 0 seconds
- Measurement: 2 seconds
- Attempts: 2
- Successes: 2
- Errors: 0
- Purpose: Confirm that `--body-file` sends valid JSON before repeating the official write stage.
- Treatment: Configuration check only; excluded from performance tables and graphs.

## L-write-c16-valid

- Start: approximately 2026-09-07 23:35:35 -05:00, derived from the end time and expected runtime
- Mid-stage resource timestamp: not captured
- End: 2026-09-07 23:36:46 -05:00
- API PID: 10920
- API CPU: 1%
- API working-set memory: 125,896 KB (approximately 122.9 MB)
- Database connections: 28 total; 10 idle in transaction, 9 idle, 7 state unavailable/NULL, 2 active
- Screenshot: not captured
- Attempts: 660
- Successes: 660
- Errors: 0
- Successful RPS: 10.749
- p50: 1,405.19 ms
- p95: 1,754.66 ms
- p99: 2,211.65 ms
- Maximum latency: 2,662.87 ms
- Error rate: 0%
- Final product-4 cart quantity: 221
- Correctness observation: The cart quantity increased far less than the number of successful HTTP writes. Concurrent read-modify-write updates likely overwrote one another. HTTP success therefore did not guarantee that every requested increment was preserved.

## L-mix-c16

- Start: 2026-09-07 23:40:48 -05:00
- Mid-stage resource timestamp: 2026-09-07 23:39:30 -05:00
- End: 2026-09-07 23:42:08 -05:00
- API PID: 10920
- API CPU: 1%
- API working-set memory: 112,000 KB (approximately 109.4 MB)
- Database connections: 28 total; 10 idle in transaction, 9 idle, 7 state unavailable/NULL, 2 active
- Screenshot: not captured
- Workload: approximately 80% `GET /api/products` and 20% `POST /api/cart`
- Attempts: 1,417
- Successes: 1,417
- Errors: 0
- Successful RPS: 23.144
- p50: 485.71 ms
- p95: 1,387.91 ms
- p99: 1,543.53 ms
- Maximum latency: 1,825.82 ms
- Error rate: 0%
- Starting cart quantity: 221
- Final cart quantity: 405
- Net observed quantity increase: 184
- Limitation: The driver randomly selected operations but did not save the operation type in the raw CSV. Concurrent cart updates also experienced lost increments, so the final quantity cannot be treated as the number of successful write requests.