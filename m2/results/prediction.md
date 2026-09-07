# M2 Workload and Capacity Prediction

Prediction recorded: 2026-09-07 15:25:56 -05:00  
Git commit: `bd1072a`
The prediction was initially recorded at commit `34b9f76` before any
load sweep. The dataset-size update was recorded at `80981dd`. The
authenticated-read correction was completed at `bd1072a`, before any
measured load stages.

## System under test

Mini Shop is a FastAPI e-commerce application backed by PostgreSQL
on Supabase. Series H runs the API on Render. Series L runs the same
API code locally while using the same Supabase database.

## Assumptions

| Parameter | Value | Basis |
|---|---:|---|
| Active fraction | 10% | Approximate e-commerce DAU/MAU assumption |
| Requests per active user per peak hour | 5 | One peak-hour session with approximately five API requests |
| Read/write mix | 80% reads / 20% writes | Required mixed workload from the assignment |
| Bytes per read response | 8,515 bytes | Measured from `GET /api/products` after seeding the catalog to 50 products |
| Bytes stored per write | 500 bytes | Planning estimate; actual cart storage is smaller and will be treated as an approximation |
| Stored copies | 1 | Current M1 architecture |
| Read path | `GET /api/products` | Product-list endpoint |
| Write path | `POST /api/cart` | Add or update a product in a customer's cart |
| Control path | `GET /health` | Cheap liveness endpoint |

## Capacity worksheet

Peak RPS is calculated as:

`active users × requests per active user per hour ÷ 3,600`

Write RPS is:

`peak RPS × 20%`

### Dataset preparation

Before the load tests, the product catalog was seeded sequentially from
3 products to 50 products. After seeding, `GET /api/products` returned
8,515 bytes. No 60-second load stages had been run when this model was
updated.

The storage/day estimate assumes the peak write rate continues for
86,400 seconds. This deliberately conservative assumption will be
revisited after measurement.

| Registered users | Active users | Peak RPS | Write RPS | Storage/day | Bandwidth |
|---:|---:|---:|---:|---:|---:|
| 10,000 | 1,000 | 1.39 | 0.28 | 12.1 MB/day | 11.8 KB/s |
| 1,000,000 | 100,000 | 138.9 | 27.8 | 1.20 GB/day | 1.18 MB/s |
| 100,000,000 | 10,000,000 | 13,889 | 2,778 | 120 GB/day | 118.3 MB/s |

## Predicted first limit

We predict that the Render API CPU will be the first observable limit
during the hosted read sweep. The application has one small API
process, while SQLAlchemy maintains a reusable database connection
pool. We therefore expect successful throughput to flatten and p99
latency to increase as Render CPU utilization rises, while PostgreSQL
connection counts remain comparatively stable.

For the local series, we expect the knee to occur at a higher offered
concurrency because the laptop provides more API compute. Network
latency between the local API and Supabase may still contribute to
request latency.