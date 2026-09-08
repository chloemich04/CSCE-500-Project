# M2 Local-Series Handoff

## Tested system

- Series: L - local FastAPI API with hosted Supabase PostgreSQL
- Application commit: `bd1072a`
- Measurement-driver commit: `4d831d8`
- Final local-results commit: to be added after committing this handoff
- API address: `http://127.0.0.1:8000`
- Python version: 3.14.7
- API process: `python.exe`
- API PID during measurements: 10920
- Dataset: 50 products
- Read-response size: 8,515 bytes
- Control path: `GET /health`
- Read path: authenticated `GET /api/products`
- Write path: authenticated `POST /api/cart`
- Mixed workload: approximately 80% product reads and 20% cart writes

Each official stage used a 10-second discarded warmup and a 60-second measurement window. Stages were separated by recovery periods. The read sweep used concurrency 1, 4, 8, 16, and 32. Concurrency 16 was repeated.

## Valid local results

| Label | Concurrency | Successful RPS | p50 (ms) | p95 (ms) | p99 (ms) | Maximum (ms) | Error rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| L-health-c2 | 2 | 201.393 | 13.64 | 20.53 | 27.14 | 106.01 | 0% |
| L-read-c1 | 1 | 2.578 | 386.08 | 406.19 | 445.22 | 487.93 | 0% |
| L-read-c4 | 4 | 10.283 | 385.28 | 402.95 | 518.39 | 854.98 | 0% |
| L-read-c8 | 8 | 20.350 | 379.43 | 405.71 | 845.95 | 1,235.66 | 0% |
| L-read-c16 | 16 | 32.682 | 467.35 | 595.38 | 770.59 | 914.34 | 0% |
| L-read-c16-repeat | 16 | 32.767 | 472.77 | 560.95 | 706.88 | 961.95 | 0% |
| L-read-c32 | 32 | 32.666 | 951.53 | 1,130.84 | 1,260.84 | 1,856.03 | 0% |
| L-write-c16-valid | 16 | 10.749 | 1,405.19 | 1,754.66 | 2,211.65 | 2,662.87 | 0% |
| L-mix-c16 | 16 | 23.144 | 485.71 | 1,387.91 | 1,543.53 | 1,825.82 | 0% |

## Local read-path knee

The local read path scaled almost linearly from concurrency 1 through 8. Throughput increased to 32.682 RPS at concurrency 16. Increasing concurrency from 16 to 32 produced no additional throughput: RPS changed from 32.682 to 32.666 while p50 increased from 467.35 ms to 951.53 ms.

The repeat at concurrency 16 produced 32.767 RPS, only approximately 0.26% above the original result. This confirms that the concurrency-16 measurement was repeatable.

The local read-path knee is therefore between concurrency 16 and 32. Concurrency 16 is the last useful stage before throughput flattens and latency rises sharply.

## Workload comparison at concurrency 16

The pure read workload achieved 32.682 RPS with a p99 of 770.59 ms. The pure write workload achieved 10.749 RPS with a p99 of 2,211.65 ms. The 80/20 mixed workload fell between them at 23.144 RPS with a p99 of 1,543.53 ms.

The write path is substantially more expensive than the product read path. Introducing approximately 20% writes reduced throughput and increased tail latency relative to the pure read stage.

## Resource observations

The idle API process used approximately 46.6 MB of working-set memory. During the measured read stages, recorded memory ranged from approximately 51.6 MB to 122.6 MB. Task Manager reported approximately 1-2% API CPU during the higher-concurrency stages.

The idle database observation showed 15 total connections. Observed connection totals rose to approximately 28 at concurrency 16 and then remained near that level. At concurrency 16, 9-10 connections were observed in the `idle in transaction` state.

The local API CPU did not approach saturation when read throughput flattened. The local evidence therefore does not support laptop CPU as the local bottleneck. The throughput plateau may instead relate to database round-trip latency, SQLAlchemy connection-pool behavior, or database transaction behavior. The hosted measurements must be compared before making the report's final primary-bottleneck claim.

Task Manager percentages and Supabase SQL queries are point-in-time samples. Some stage timestamps or screenshots were not captured, as documented in `notes.md`.

## Write-path correctness observation

The first official write attempt was invalid because an early `--body-file` implementation did not send the loaded JSON body. All 2,452 requests returned HTTP 422. That row is retained in `summary.csv` for transparency but excluded from performance tables and graphs. A two-second diagnostic verified the correction before the valid write stage.

The valid write stage reported 660 successful HTTP responses, but the cart quantity increased by much less than the number of attempted increments. Concurrent requests likely performed overlapping read-modify-write operations and overwrote one another. HTTP success therefore did not guarantee that every requested cart increment was preserved. This is a correctness limitation of the current baseline.

The mixed driver also does not save whether each raw sample was a read or write. Its configured random selection was 80/20, but the exact measured operation counts cannot be reconstructed from its raw CSV.

## Files for the combined report

- `m2/results/local-summary.csv`: valid local stages
- `m2/results/summary.csv`: complete history, including diagnostic runs
- `m2/results/L-*.requests.csv`: raw request latencies
- `m2/results/notes.md`: timestamps and resource observations
- `m2/results/local-L-*.png`: available local screenshots
- `m2/results/prediction.md`: pre-measurement model and prediction
- `m2/requests/cart-add.json`: reproducible cart-write request body

When combining results, use the primary read rows at concurrency 1, 4, 8, 16, and 32 for the main curves. Show the concurrency-16 repeat separately or mention it as repeatability evidence. Do not average hosted and local measurements together.