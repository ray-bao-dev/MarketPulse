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

### Sizing

Training uses PyTorch on CPU. Use at least **2 GB RAM**; 4 GB recommended for larger datasets.

## Usage

1. Deploy the service and open its public URL
2. Confirm **Status: idle** and database is linked (`GET /health` → `database_configured: true`)
3. Enter symbols, timeframe (5Min), start date
4. Click **Run training pipeline**
5. When complete, download `patterns.onnx` and `manifest.json`
6. Upload ONNX to classifier storage and set `MODEL_PATH` on **MarketPulse-Classifier**

## Prerequisites

Worker must have synced **5Min** bars for your symbols (`PRIORITY_INTRADAY_TIMEFRAMES=5Min` on worker).

## Local run (optional)

Requires PostgreSQL with bars and TA-Lib installed:

```bash
cd trainer
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://...
export PYTHONPATH=../classifier:..
python run.py
```

Open http://localhost:8090
