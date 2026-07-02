# Worker service

Syncs historical market data from Alpaca into PostgreSQL.

## Railway setup

| Setting | Value |
|---|---|
| Root Directory | `.` (repository root) |
| Dockerfile path | `worker/Dockerfile` |

The worker shares the `backend/marketpulse/` Python package with the API service.

Required variables: `DATABASE_URL`, `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `SYNC_INTERVAL_MINUTES` (optional, default 5).
