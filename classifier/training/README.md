# Offline training pipeline

Training runs **locally** (or in a manual CI job). It is not deployed to Railway.

## Prerequisites

From the `classifier/` directory:

```bash
python -m venv .venv
# Windows Git Bash:
source .venv/Scripts/activate
# Windows CMD:
# .venv\Scripts\activate.bat

pip install -r requirements.txt
pip install -r training/requirements.txt
```

Scripts add `classifier/` to `sys.path` automatically — you do **not** need `PYTHONPATH=.` when running `python training/...py` from `classifier/`.

**TA-Lib** (Python `>=0.6.5` bundles the C library on Linux; local dev may still need the system library):

- Windows: `pip install TA-Lib` (wheel) or [cgohlke/talib-build releases](https://github.com/cgohlke/talib-build/releases)
- macOS: `brew install ta-lib` optional; `pip install "TA-Lib>=0.6.5"` usually enough
- Linux Docker: `pip install "TA-Lib>=0.6.5"` only
- Linux local (no wheel): [`.deb` from ta-lib.org](https://ta-lib.org/install/) or build C lib from source, then `pip install "TA-Lib>=0.6.5"`

## Recommended workflow (TA-Lib weak labels)

### 1. Ensure 5Min bars are in PostgreSQL

The worker syncs **5Min only for priority symbols** (`SPY`, `QQQ`, watchlist). Set in `backend/.env`:

```bash
PRIORITY_SYMBOLS=SPY,QQQ,AAPL,MSFT,GOOGL,AMZN,NVDA
PRIORITY_INTRADAY_TIMEFRAMES=5Min
```

### 2. Generate dataset

From PostgreSQL:

```bash
cd classifier
python training/generate_talib_dataset.py \
  --database-url "postgresql+asyncpg://postgres:postgres@localhost:5432/marketpulse" \
  --symbols SPY,QQQ,AAPL \
  --timeframe 5Min \
  --start 2025-01-01 \
  --output artifacts
```

Or from exported JSON:

```bash
curl "http://localhost:8000/api/market/bars?symbol=AAPL&timeframe=5Min&start=2025-01-01" \
  > training/data/aapl-5min.json

python training/generate_talib_dataset.py --bars training/data/aapl-5min.json --output artifacts
```

**Filters applied:**
- TA-Lib signal magnitude ≥ 100 (full match)
- Exactly one pattern on the completion bar (ambiguous windows dropped)
- Stratified cap per class (default 10,000)
- Walk-forward split by month → `train.npz`, `val.npz`, `test.npz`

Outputs:
- `artifacts/train.npz`, `val.npz`, `test.npz`
- `artifacts/manifest.json`
- `artifacts/splits.json` (class counts per split)

### 3. Train

```bash
python training/train.py --dataset-dir artifacts --output artifacts --epochs 12
```

Uses `train.npz` for training and `val.npz` for validation accuracy each epoch.

### 4. Export ONNX

```bash
python training/export_onnx.py --weights artifacts/candle_cnn.pt --manifest artifacts/manifest.json --output models/patterns.onnx
```

Copy `artifacts/manifest.json` to `models/manifest.json` if needed.

### 5. Deploy model artifact

1. Upload `models/patterns.onnx` to Railway Object Storage (or mount a volume)
2. Set on the classifier service:
   - `MODEL_PATH=/app/models/patterns.onnx`
   - `INFERENCE_MODE=onnx`
3. Redeploy **MarketPulse-Classifier** only

Do **not** commit large `.onnx` / `.pt` files to git.

## Legacy rule-based labeling

The older `--bars` path uses hand-tuned rules in `training/labels.py` (same as inference fallback). Prefer TA-Lib generation for scale.

```bash
python training/train.py --bars training/data/aapl-5min.json --output artifacts
```

## Gold-set evaluation (human review)

**Do not train on the gold set.** Use it only to measure marker quality and tune thresholds.

### Build a review sample

1. Run detection on a held-out range (use `test.npz` months or AI Analysis tab)
2. Randomly sample 50–100 windows per pattern class from `test.npz` or live detections
3. Export sample timestamps + predicted labels to a spreadsheet or JSON

### Review criteria

For each sample, mark:
- **correct** — pattern name matches the chart
- **wrong** — false positive
- **wrong_class** — a pattern exists but label is incorrect

### Metrics (optimize these, not accuracy)

| Metric | Target (v1) |
|---|---|
| Precision @ confidence ≥ 0.65 | ≥ 70% on gold set for top 3 patterns |
| High-confidence marker count | Enough to be useful, not noise |
| Per-pattern precision | Identify weak classes to drop or retrain |

**Precision** = correct / (correct + wrong + wrong_class)

Accuracy is misleading because `none` dominates the dataset.

### Threshold tuning

1. Deploy ONNX model with default `CONFIDENCE_THRESHOLD=0.65`
2. On gold set, sweep thresholds: 0.55, 0.65, 0.75, 0.85
3. Pick the lowest threshold where precision ≥ 70% for your priority patterns
4. Set `CONFIDENCE_THRESHOLD` on the classifier service

### Iterate

1. Fix labeling issues in `generate_talib_dataset.py` filters
2. Regenerate dataset → retrain → re-export ONNX
3. Re-run gold-set review (same held-out samples if possible)

## MVP pattern classes

| Label | TA-Lib source |
|---|---|
| none | no pattern on completion bar |
| hammer | CDLHAMMER |
| doji | CDLDOJI |
| bullish_engulfing | CDLENGULFING > 0 |
| bearish_engulfing | CDLENGULFING < 0 |
| shooting_star | CDLSHOOTINGSTAR |
| morning_star | CDLMORNINGSTAR |

Expand to more TA-Lib patterns only after v1 precision looks sane on the gold set.
