# MarketPulse

Stock market data dashboard with PostgreSQL-backed historical storage synced from Alpaca.

## Services

Each service has its own directory and `railway.toml`:

| Directory | Railway service | Root Directory |
|---|---|---|
| [`backend/`](backend/) | MarketPulse-BackEnd | `backend` |
| [`worker/`](worker/) | MarketPulse-Worker | `.` (repo root) |
| [`frontend/`](frontend/) | MarketPulse-FrontEnd | `frontend` |

Plus **PostgreSQL** from Railway (`railway add --database postgres`).

## Local development

```bash
# PostgreSQL required locally, or use Railway DATABASE_URL
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
cd backend && PYTHONPATH=. python ../worker/run.py

# Frontend
cd frontend && npm install && npm run dev
```

## Railway deploy order

1. Add PostgreSQL database
2. Deploy **BackEnd** — link `DATABASE_URL`, Alpaca keys, `CORS_ORIGINS`
3. Deploy **Worker** — same `DATABASE_URL` and Alpaca keys; root directory = repo root
4. Deploy **FrontEnd** — set `VITE_API_URL` to BackEnd URL

See each service's `README.md` for details.
