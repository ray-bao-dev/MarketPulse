# MarketPulse Classifier

Inference service for candlestick pattern detection. Runs separately from the API, worker, and frontend.

## Endpoints

- `GET /health` — service and model status
- `POST /v1/detect` — pattern detection on an OHLCV bar array (Alpaca/DB shape)

## Inference modes

| Mode | Env | Behavior |
|---|---|---|
| `auto` (default) | `INFERENCE_MODE=auto` | Use ONNX if `MODEL_PATH` exists, else rule-based stub |
| `onnx` | `INFERENCE_MODE=onnx` | Require ONNX model file |
| `rules` | `INFERENCE_MODE=rules` | Rule-based detectors (integration / fallback) |

## Environment

```bash
PORT=8080
MODEL_PATH=/app/models/patterns.onnx   # optional until trained model uploaded
MANIFEST_PATH=/app/models/manifest.json
CONFIDENCE_THRESHOLD=0.65
INFERENCE_MODE=auto
```

## Local run

```bash
cd classifier
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python run.py
```

## Railway

- Root Directory: `classifier`
- Set `CLASSIFIER_URL` on the backend to this service's URL

## Model updates (offline)

1. Train with scripts in `training/` (not deployed)
2. Export ONNX → upload to object storage
3. Set `MODEL_PATH` (or mount volume) and update `models/manifest.json`
4. Redeploy classifier service only

See `training/README.md` for the training workflow.
