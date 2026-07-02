# MarketPulse

Stock market data dashboard with PostgreSQL-backed historical storage synced from Alpaca.

## Services

Each service has its own directory and `railway.toml`:

| Directory | Railway service | Root Directory |
|---|---|---|
| [`backend/`](backend/) | MarketPulse-BackEnd | `backend` |
| [`worker/`](worker/) | MarketPulse-Worker | `.` (repo root) |
| [`frontend/`](frontend/) | MarketPulse-FrontEnd | `frontend` |
| [`classifier/`](classifier/) | MarketPulse-Classifier | `classifier` |
| [`trainer/`](trainer/) | MarketPulse-Trainer | `.` (repo root) |

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

# Classifier (separate terminal)
cd classifier && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt && python run.py
```

## Railway deploy order

1. Add PostgreSQL database
2. Deploy **BackEnd** — link `DATABASE_URL`, Alpaca keys, `CORS_ORIGINS`, and `CLASSIFIER_URL`
3. Deploy **Worker** — same `DATABASE_URL` and Alpaca keys; root directory = repo root
4. Deploy **Classifier** — set `MODEL_PATH` when ONNX artifact is available; no DB required
5. Deploy **Trainer** (optional) — link `DATABASE_PRIVATE_URL`; web UI to train and download ONNX
6. Deploy **FrontEnd** — set `VITE_API_URL` to BackEnd URL

See each service's `README.md` for details.
