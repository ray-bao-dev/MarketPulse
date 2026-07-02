# MarketPulse Trainer

Single Railway service: **simple web UI + dataset generation + CNN training + ONNX export**.

Reads OHLCV bars from the same PostgreSQL database as the API/worker (uses Railway internal `DATABASE_PRIVATE_URL`).

## Railway setup

| Setting | Value |
|---|---|
| Root Directory | `.` (repository root) |
| Dockerfile path | `trainer/Dockerfile` |

### Variables

Link the PostgreSQL service (same as BackEnd/Worker):

| Variable | Source |
|---|---|
| `DATABASE_PRIVATE_URL` | PostgreSQL → **private** URL (preferred on Railway) |
| `DATABASE_URL` | PostgreSQL → public URL (fallback) |

Optional:

| Variable | Default |
|---|---|
| `DEFAULT_SYMBOLS` | `SPY,QQQ,AAPL` |
| `DEFAULT_START` | `2025-01-01` |
| `ARTIFACTS_DIR` | `/app/artifacts` |
| `CLASSIFIER_URL` | Classifier service URL — auto `POST /v1/reload` after training |

### Sizing

Training uses PyTorch on CPU. Use at least **2 GB RAM**; 4 GB recommended for larger datasets.

## Usage

1. Deploy the service and open its public URL
2. Confirm **Status: idle** and database is linked (`GET /health` → `database_configured: true`)
3. Enter symbols, timeframe (5Min), start date
4. Click **Run training pipeline**
5. When complete, download `patterns.onnx` and `manifest.json` (optional — model is saved to PostgreSQL)
6. Call **Classifier** `POST /v1/reload` or redeploy classifier to load the new active model from the database

The trainer writes the ONNX file and manifest to the `model_artifacts` table and marks it as **active**. The classifier reads that row on startup.

## Prerequisites

Worker must have synced **5Min** bars for your symbols (`PRIORITY_INTRADAY_TIMEFRAMES=5Min` on worker).

## Local run (optional)

Requires PostgreSQL with bars and TA-Lib installed (Docker image pins `python:3.12-slim-bookworm` for `libta-lib0` apt packages).

```bash
cd trainer
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://...
export PYTHONPATH=../classifier:..
python run.py
```

Open http://localhost:8090
