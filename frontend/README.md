# Frontend service

React dashboard for MarketPulse.

## Railway setup

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Dockerfile path | `Dockerfile` |

Required variables: `VITE_API_URL` = BackEnd public URL (no trailing slash).

Build bakes `VITE_API_URL` into the static bundle at deploy time.
