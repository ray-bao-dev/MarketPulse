# MarketPulse Classifier

Inference service for candlestick pattern detection.

## Endpoints

- `GET /health` — service and model status
- `POST /v1/reload` — reload active model from PostgreSQL (after training)
- `POST /v1/detect` — pattern detection on OHLCV bars

## Model loading (startup + reload)

Priority:

1. **PostgreSQL** — active row in `model_artifacts` (recommended on Railway)
2. `MODEL_URI` / `MANIFEST_URI` — HTTP download fallback
3. Local `MODEL_PATH` / bundled `models/` — rules fallback if no ONNX

## Railway variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_PRIVATE_URL` | Yes (with trainer) | Same PostgreSQL as API/worker |
| `DATABASE_URL` | Fallback | Public DB URL if private unavailable |

Optional:

| Variable | Default |
|---|---|
| `MODEL_DIR` | `/app/models` |
| `INFERENCE_MODE` | `auto` |
| `CONFIDENCE_THRESHOLD` | `0.65` |
| `MODEL_URI` | — (only if not using DB) |

Link PostgreSQL to this service. On startup it loads the active model from `model_artifacts`.

After training on the **Trainer** service, call `POST /v1/reload` on the classifier (or redeploy) to pick up the new model.

## Local run

```bash
cd classifier
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://...
python run.py
```

Set `CLASSIFIER_URL` on the backend to this service's URL.
