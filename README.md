# MarketPulse

A market data dashboard for stock research and future prediction workflows. Pulls live and historical data from the [Alpaca Markets API](https://alpaca.markets/).

## Stack

- **Frontend** — React + Vite, TradingView Lightweight Charts
- **Backend** — Python FastAPI, proxies Alpaca (keeps API keys server-side)

A Python trading/heuristics API can be added alongside the backend later without changing the dashboard.

## Quick start

### 1. Alpaca credentials

Sign up at [Alpaca](https://app.alpaca.markets) and create API keys (paper account is fine for market data).

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your ALPACA_API_KEY and ALPACA_API_SECRET

uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/market/status` | Whether Alpaca credentials are configured |
| `GET /api/market/snapshots?symbols=AAPL,MSFT` | Latest price snapshots |
| `GET /api/market/bars?symbol=AAPL&timeframe=1Day&limit=100` | Historical OHLCV bars |
| `GET /api/market/search?q=apple` | Symbol search |
| `GET /api/market/quote/{symbol}` | Latest quote |

## Dashboard features

- Watchlist with live snapshots (refreshes every 30s)
- Symbol search to add tickers
- Candlestick chart with 1H / 1D / 1W timeframes
- OHLCV stats and recent bars table

## Project layout

```
MarketPulse/
├── backend/          # FastAPI + Alpaca client
│   └── app/
├── frontend/         # React dashboard
└── README.md
```
