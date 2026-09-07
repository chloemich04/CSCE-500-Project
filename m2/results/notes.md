# M2 Resource Notes

## Test configuration

- Git commit: `80981dd`
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
- API working-set memory:47,728K
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