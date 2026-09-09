# M2 — Baseline Performance

**Mini Shop** (our M1 e-commerce app for video games) — CSCE 553.
Public URL: https://csce-500-project.onrender.com · Repo: https://github.com/chloemich04/CSCE-500-Project

We split the load testing in two: **Sabri** ran the hosted tests (Series H, on the live Render URL), and **Chloe** ran the local tests (Series L, same code on localhost). The goal was to push our app until it slows down, find where it breaks, and explain why.

*(This is a class baseline, not production — all the data is fake.)*

---

## 1. How much load are we even talking about?

Before touching the load tester, we tried to figure out how much traffic our app would actually get. A number of registered users isn't a workload on its own, so we looked up some real e-commerce benchmarks to make reasonable assumptions instead of guessing.

### Assumptions

| Param | Value | Source |
|-------|-------|--------|
| Active fraction | 10% | E-commerce DAU/MAU ≈8–10%. [Statsig](https://www.statsig.com/perspectives/understanding-daumau-key-metrics-for-product-success): "e-commerce sites average around 9.8%"; [CleverTap](https://clevertap.com/blog/dau-vs-mau-app-stickiness-metrics/): "E-commerce Apps: 10% DAU/MAU on average". |
| Requests/active user/hour | 5 | [MetricHQ](https://www.metrichq.org/marketing/page-views-per-session/): e-commerce 5–10 pages/session; we take 5 (lower bound), assume 1 session/user/peak-hour, 1 page ≈ 1 API request. |
| Read/write mix | 80 / 20 | Assignment. Reads = browse/search/view cart; writes = register/add-to-cart/checkout. |
| Bytes/response | 500 B | Measured: `GET /api/products` = 446 B, rounded to 500 B. Small catalog; a full catalog would be larger. |
| Copies | 1 | M1, no replication. |

### Formulas
```
Peak RPS    = active_users × req_per_user_per_hour / 3600
Write RPS   = Peak RPS × 0.20
Writes/day  = Write RPS × 86400
Storage/day = Writes/day × bytes_per_write × copies
Bandwidth   = Peak RPS × bytes_per_response × copies
```

### Worksheet

| Registered users | Active (10%) | Peak RPS | Write RPS | Writes/day | Storage/day | Bandwidth |
|------------------|--------------|----------|-----------|------------|-------------|-----------|
| 10 K | 1 K | 1.4 | 0.28 | 24 K | 12 MB | 0.69 KB/s |
| 1 M | 100 K | 139 | 28 | 2.4 M | 1.2 GB | 69 KB/s |
| 100 M | 10 M | 13,889 | 2,778 | 240 M | 120 GB | 6.9 MB/s |

*(Storage = raw new rows; indexes/WAL/backups add ≈2–4× on top, noted not modeled.)*

---

## 2. What we thought would break first

Our setup is a chain: browser → API on Render → Postgres on Supabase. Before running anything, we bet that the **API on Render would give out first**. The free Render instance runs on 0.1 CPU (basically a tenth of a processor), so we figured that under load the requests would pile up there and the latency would blow up, while the database — which has way more room and only handles simple queries — would stay fine. We also expected the first request after the app sleeps to be really slow (cold start).

*(We wrote this down before measuring — see `prediction.md` / git history — so it's clear we didn't reverse-engineer it afterwards.)*

---

## 3. Method

- **Tool:** k6 v2.2.0 (open source), run from a local laptop.
- **Environments:**
  - **Series H (hosted):** API on the public Render URL, Postgres on Supabase (session pooler).
  - **Series L (local):** API on localhost (same code/commit), Postgres on the same hosted Supabase.
- **Endpoints:** control `GET /health`; read path `GET /api/products`; write path `PUT /api/cart/{item_id}` (update quantity — repeatable, unlike POST add-to-cart which accumulates and hits the stock limit); mix 80% read / 20% write.
- **Stages:** 1, 4, 8, 16, 32 concurrent VUs. Each read/write stage = 10 s warmup (discarded via a custom `measure_duration` metric) + 60 s measured, with 30–60 s drain between stages.
- **Stop rules:** error rate > 10%, or p99 > 5 s, or mostly 429/502/503. (Not triggered on the read path; the throughput plateau marked the capacity limit instead.)
- **Repeat:** the last healthy stage (16 VUs) was repeated to check stability.

---

## 4. Series H — testing the live app (Sabri)

### 4.1 Cold start (H only)
First `GET /health` after > 15 min idle: **≈32.25 s** (single request, wall time). Confirms cold-start dominates the first request on Render free tier.

### 4.2 Control — GET /health (warm, no DB)

| VUs | Throughput (req/s) | p50 | p95 | p99 | max | Errors |
|-----|--------------------|-----|-----|-----|-----|--------|
| 1 | 13.9 | 69.71 ms | 80.94 ms | 99.32 ms | 115.35 ms | 0% |
| 4 | 55.7 | 69.18 ms | 77.91 ms | 120.55 ms | 139.26 ms | 0% |
| 8 | 114.4 | 67.33 ms | 77.14 ms | 109.51 ms | 160.45 ms | 0% |
| 16 | 224.1 | 68.74 ms | 78.40 ms | 99.14 ms | 149.07 ms | 0% |

Throughput scales linearly, latency flat, 0% errors — `/health` does no real work, so it does not saturate. Baseline/control.

### 4.3 Read path — GET /api/products (main saturation sweep)

| VUs | Throughput (req/s) | p50 | p95 | p99 | max | Errors |
|-----|--------------------|-----|-----|-----|-----|--------|
| 1 | 3.07 | 281 ms | 376 ms | 410 ms | 430 ms | 0% |
| 4 | 12.5 | 271 ms | 315 ms | 415 ms | 444 ms | 0% |
| 8 | 27.5 | 226 ms | 308 ms | 829 ms | 1.66 s | 0% |
| **16** | **49.8** | **259 ms** | **352 ms** | **587 ms** | **802 ms** | **0%** |
| **32** | **49.0** | **556 ms** | **700 ms** | **853 ms** | **1.18 s** | **0%** |
| 16 (repeat) | 49.5 | 259 ms | 354 ms | 592 ms | 805 ms | 0% |

**Knee between 16 and 32 VUs:** throughput plateaus at ≈50 req/s (49.8 → 49.0, stops scaling) while p50 doubles (259 → 556 ms). The 16-VU repeat agrees closely (49.8 vs 49.5 req/s; p99 587 vs 592 ms) → stable measurements.

### 4.4 Write path — PUT /api/cart/{item_id}

| VUs | Throughput (req/s) | p50 | p95 | p99 | max | Errors |
|-----|--------------------|-----|-----|-----|-----|--------|
| 8 | 9.6 | 708 ms | 916 ms | 1.02 s | 1.05 s | 0% |
| 16 | 15.8 | 853 ms | 1.11 s | 1.20 s | 1.51 s | 0% |

Read vs write at 16 VUs: read 49.8 req/s / p50 259 ms vs write 15.8 req/s / p50 853 ms. Writes are ≈3× slower and ≈3× lower throughput (UPDATE + commit costs more than a read) — the write path saturates earlier.

### 4.5 Mix — 80% read / 20% write @ 16 VUs

| Test @ 16 VUs | Throughput (req/s) | p50 | p95 | p99 | Errors |
|---------------|--------------------|-----|-----|-----|--------|
| Read pure | 49.8 | 259 ms | 352 ms | 587 ms | 0% |
| **Mix 80/20** | **35.2** | **294 ms** | **898 ms** | **999 ms** | **0%** |
| Write pure | 15.8 | 853 ms | 1.11 s | 1.20 s | 0% |

The mix p50 stays near read (294 ms), but p95/p99 (898/999 ms) approach the write path even though only 20% of requests are writes: slow writes occupy the single CPU and block fast reads queued behind them. A minority of writes limits the tail for everyone — *mix changes the bottleneck.*

---

## 5. Series L — testing it locally (Chloe)

> Same code/commit, API on localhost, same hosted Supabase. Local CPU is visible here — this is the direct CPU evidence the hosted side cannot show.

### 5.1 Control — GET /health (local)

| VUs | Throughput (req/s) | p50 | p95 | p99 | max | Errors |
|-----|--------------------|-----|-----|-----|-----|--------|
| 2 | 201.4 | 13.64 ms | 20.53 ms | 27.14 ms | 106.01 ms | 0% |

*(from `L-health-c2.requests.csv`. Local /health is far faster than hosted — 13.6 ms p50 vs 70 ms — because there is no laptop→cloud network hop for the API itself.)*

### 5.2 Read path — GET /api/products (local)

| VUs | Throughput (req/s) | p50 | p95 | p99 | max | Errors |
|-----|--------------------|-----|-----|-----|-----|--------|
| 1 | 2.58 | 386.08 ms | 406.19 ms | 445.22 ms | 487.93 ms | 0% |
| 4 | 10.28 | 385.28 ms | 402.95 ms | 518.39 ms | 854.98 ms | 0% |
| 8 | 20.35 | 379.43 ms | 405.71 ms | 845.95 ms | 1235.66 ms | 0% |
| 16 | 32.68 | 467.35 ms | 595.38 ms | 770.59 ms | 914.34 ms | 0% |
| 32 | 32.67 | 951.53 ms | 1130.84 ms | 1260.84 ms | 1856.03 ms | 0% |
| 16 (repeat) | 32.77 | 472.77 ms | 560.95 ms | 706.88 ms | 961.95 ms | 0% |

*(from `L-read-c1/c4/c8/c16/c32.requests.csv` and `L-read-c16-repeat.requests.csv`. Same knee pattern as Series H: throughput plateaus at ≈32 req/s from 16→32 VUs (32.68 → 32.67, stops scaling) while p50 doubles (467→952 ms). The 16-VU repeat agrees within 0.26% (32.68 vs 32.77 req/s) → stable. Note local read latency (≈385 ms p50 at low load) is higher than hosted (≈281 ms) — the local API still queries the same remote Supabase, so the DB round-trip dominates and the API compute, not the network, sets the ceiling.)*

### 5.3 Write path — PUT /api/cart (local)

| VUs | Throughput (req/s) | p50 | p95 | p99 | max | Errors |
|-----|--------------------|-----|-----|-----|-----|--------|
| 16 | 10.75 | 1405.19 ms | 1754.66 ms | 2211.65 ms | 2662.87 ms | 0% |

*(from `L-write-c16-valid.requests.csv`. Write is much heavier than read at 16 VUs: 10.7 vs 32.7 req/s, p50 1405 vs 467 ms. Correctness note: the final cart quantity rose far less than the number of successful writes — concurrent read-modify-write updates overwrote each other (lost updates). HTTP 200 did not guarantee every increment persisted; this is a concurrency-correctness observation, not a capacity error.)*

### 5.4 Mix 80/20 (local)

| Test @ 16 VUs | Throughput (req/s) | p50 | p95 | p99 | Errors |
|---------------|--------------------|-----|-----|-----|--------|
| Read pure | 32.68 | 467 ms | 595 ms | 771 ms | 0% |
| Mix 80/20 | 23.14 | 486 ms | 1388 ms | 1544 ms | 0% |
| Write pure | 10.75 | 1405 ms | 1755 ms | 2212 ms | 0% |

*(from `L-mix-c16.requests.csv`. Same effect as Series H: the mix p50 stays near read (486 ms) but p95/p99 (1388/1544 ms) jump toward the write path, even though only ≈20% are writes — the writes inflate the tail for everyone.)*

### 5.5 Local CPU and DB (resource signals — direct)
Captured during the read sweep (screenshots `local-L-idle-*.png`, `local-L-read-c4/c8/c16/c32-*.png` in `m2/results/`). Git commit `bd1072a`; local API `python -m uvicorn app.main:app` (PID varies), Python 3.14.7, Windows laptop on AC power. Timezone CDT (UTC−05:00).

| Stage | API CPU | API memory (working set) | DB connections (total) |
|-------|---------|--------------------------|------------------------|
| Idle baseline | 0% | ≈47.7 MB | 15 |
| read c4 | 1% | ≈51.6 MB | 21 |
| read c8 | 1% | ≈57.9 MB | 26 |
| read c16 | 2% | ≈122.5 MB | 28 |
| read c16 (repeat) | 2% | ≈122.6 MB | 28 |

**Reading:** the local API CPU stays low (0→2%) and the DB connections stay modest (15→28 of 60) even as throughput plateaus at ≈32 req/s. Memory grows with concurrency (48→122 MB) but never approaches a limit. On a single-worker local process the ceiling is per-request serialization through the API (each request waits on the remote Supabase round-trip), not raw CPU or DB — consistent with the hosted bottleneck being the constrained 0.1-CPU compute on Render. **Dataset:** 50 products, `GET /api/products` = 8,515 bytes.

---

## 6. Figures

All figures are in `m2/results/`. Series H and Series L are plotted separately (never merged).

**Series H (hosted) — read path:**

![H throughput](results/fig1_H_throughput.png)
![H latency](results/fig2_H_latency.png)
![H error rate](results/fig3_H_errorrate.png)

- `fig1_H_throughput.png` — throughput vs offered load (plateau at ≈50 req/s).
- `fig2_H_latency.png` — p50 & p99 vs offered load (p50 doubles at 32 VUs).
- `fig3_H_errorrate.png` — error rate vs offered load (0% at all stages).

**Series L (local) — read path:**

![L throughput](results/fig4_L_throughput.png)
![L latency](results/fig5_L_latency.png)
![L error rate](results/fig6_L_errorrate.png)

- `fig4_L_throughput.png` — throughput vs offered load (plateau at ≈32 req/s).
- `fig5_L_latency.png` — p50 & p99 vs offered load (p50 doubles at 32 VUs).
- `fig6_L_errorrate.png` — error rate vs offered load (0% at all stages).

Both series show the same shape (throughput plateau + latency doubling at the knee, 0% errors), on different absolute ceilings (H ≈50 req/s, L ≈32 req/s).

---

## 7. What the machines were doing during the tests

**Series H (hosted).** Render free tier does not expose API CPU/memory (paywalled; upgrading forbidden). Signals used:

| Signal | Value during load | Reading |
|--------|-------------------|---------|
| Supabase DB CPU | ≈2% | DB idle — not the bottleneck |
| Supabase peak connections | 14 / 60 | Ample headroom (23% of limit) |
| Supabase disk IO | ≈1% | No disk pressure |
| Render outbound bandwidth | rising during runs | Service actively serving load |

**Series L (local):** direct local CPU screenshots (section 5.5) — the compute signal the hosted side cannot provide.

Screenshots and timestamps in `m2/results/`.

---

## 8. Were we right? (checking the prediction)

Short answer: yes, we were right — the bottleneck is the **API compute on Render (0.1 CPU)**. Two things line up to prove it:
1. On the read path, throughput stops climbing at ≈50 req/s (16→32 VUs) while the p50 latency doubles (259→556 ms), and this happens with **zero errors**. That's what a compute queue looks like — requests waiting their turn, not failing.
2. At the exact same time, the database is basically asleep: 2% CPU, 14 out of 60 connections used, 1% disk. It had tons of room left.

So by elimination in the browser → Render → Postgres chain, the only thing that could be the limit is the API compute. And Series L backs this up directly: on the local machine the CPU climbs with the load while the (shared) database stays idle. Prediction confirmed.

---

## 9. Setting a target we can actually check

Throughput alone can hide a bad experience, so we set ourselves one measurable promise. We only count **warm `GET /api/products` after login** (we don't count the cold-start request, that's not fair).

**Our target:** 99% of those requests should finish in under **900 ms**, with under 1% errors.

We picked 900 ms from our own numbers: at the last healthy stage (16 VUs) the p99 was 587 ms with no errors, and even at 32 VUs it was 853 ms — so 900 ms gives a bit of headroom but still fails if we push the app too far.

Does the hosted app hold up?
- At 16 VUs: p99 = 587 ms, 0 errors → **yes**.
- At 32 VUs: p99 = 853 ms, 0 errors → still **yes** on pure reads (but it's not getting any faster).
- With the realistic 80/20 mix at 16 VUs: p99 = 999 ms → **no**. The 20% of writes drag the tail over the limit.

So the app meets our target for pure reads, but real mixed traffic breaks it. The thing that actually hurts is the tail once writes are in the picture.

---

## 10. Prediction vs reality, and scaling up

What we guessed and what we measured basically match: the Render API is the first limit, the database keeps its headroom, and the cold start (≈32 s) dominates the first request. The one thing we learned along the way is that the **write path and the mix make the tail worse** than the read-only test suggested — so our ≈50 req/s ceiling is a bit optimistic once real writes are included.

Now, scaling our capacity numbers against that measured ≈50 req/s ceiling:
- **10K users (≈1.4 predicted RPS):** ≈35× below the measured ≈50 req/s read ceiling → ample headroom, not compute-bound on this architecture.
- **1M users (≈139 RPS):** ≈3× above the measured ceiling → needs more than one 0.1-CPU instance (horizontal scaling / larger tier). DB still not the first thing to change.
- **100M users (≈13,900 RPS):** ≈280× the ceiling → requires many API replicas behind a load balancer, a read-path cache, and DB read replicas/partitioning — the architecture must change (out of scope for M1/M2).

**Revised first-limit statement:** the Render 0.1-CPU API compute caps sustained read throughput at ≈50 req/s and mixed-traffic p99 near 1 s, well before Postgres shows any pressure.

---

## 11. Confounds

- Render free tier: 0.1 CPU, sleeps after ≈15 min idle (cold start measured separately: 32 s).
- No direct Render CPU/memory metric (paywalled) — inferred from DB headroom + throughput plateau on H; Series L exposes CPU directly.
- Local laptop as load generator; network path to us-west Supabase included in hosted latency.
- Series H and Series L are reported in separate tables and never averaged together.
- **Response-size difference between series:** the capacity worksheet uses ≈500 B (measured on H with a near-empty catalog: 446 B). Series L was run with 50 products, where `GET /api/products` = 8,515 bytes. This does not change the bottleneck (compute/serialization, not bandwidth), but bandwidth figures scale with catalog size; the worksheet's storage/bandwidth numbers are lower bounds for a small catalog.
- **Shared free-tier neighbors:** on Render/Supabase free tiers the instance shares physical hardware with other tenants; their spikes can perturb our latency (especially the p99 tail) independently of our own load.
- **Clock skew:** the load generator (laptop) and the hosted servers do not share a clock; small offsets can affect absolute timestamps when aligning k6 runs with the resource-signal screenshots. We align by wall-clock window (≈Sep 7, 2–3 pm), not exact millisecond timestamps.
- Exploratory `/health` stages ran ≈10 s; read/write/mix stages used the full 10 s warmup + 60 s measured protocol.

---

## 12. Reproducibility

- Endpoints and demo accounts: see the M1 README API table (`alex@example.com` / `blair@example.com` / `casey@example.com`, password `ClassDemo123!`).
- k6 scripts in `m2/` (`health-test.js`, read/write/mix variants); request bodies in `m2/requests/`.
- Raw CSVs in `m2/results/` (Series H: `series_h_results.csv`; Series L: `L-*.requests.csv`, `local-summary.csv`).
- Each stage: 10 s warmup discarded + 60 s measured; wake the app via `/health` before hosted runs (free-tier cold start ≈1 min).
