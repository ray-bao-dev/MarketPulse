import { useCallback, useEffect, useState } from "react";
import {
  getBars,
  getMarketStatus,
  getSnapshots,
  getSyncStatus,
  type AlpacaBar,
  type AlpacaSnapshot,
  type SyncStatus,
} from "../api/client";
import { PriceChart } from "../components/PriceChart";
import { SymbolSearch } from "../components/SymbolSearch";
import { Watchlist } from "../components/Watchlist";

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"];
const TIMEFRAMES = [
  { label: "1H", value: "1Hour" },
  { label: "1D", value: "1Day" },
  { label: "1W", value: "1Week" },
] as const;

function formatPrice(value: number | undefined): string {
  if (value === undefined) return "—";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatVolume(value: number | undefined): string {
  if (value === undefined) return "—";
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function Dashboard() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [activeSymbol, setActiveSymbol] = useState(DEFAULT_SYMBOLS[0]);
  const [snapshots, setSnapshots] = useState<Record<string, AlpacaSnapshot>>({});
  const [bars, setBars] = useState<AlpacaBar[]>([]);
  const [timeframeIdx, setTimeframeIdx] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);

  const timeframe = TIMEFRAMES[timeframeIdx];

  const refreshSnapshots = useCallback(async (symbolList: string[]) => {
    const data = await getSnapshots(symbolList);
    setSnapshots(data);
  }, []);

  const refreshBars = useCallback(
    async (symbol: string, tf: (typeof TIMEFRAMES)[number]) => {
      const data = await getBars(symbol, tf.value);
      setBars(data);
    },
    [],
  );

  useEffect(() => {
    getMarketStatus()
      .then((status) => setConfigured(status.configured))
      .catch(() => setConfigured(false));
  }, []);

  useEffect(() => {
    if (!configured) return;

    getSyncStatus()
      .then(setSyncStatus)
      .catch(() => undefined);

    const interval = setInterval(() => {
      getSyncStatus()
        .then(setSyncStatus)
        .catch(() => undefined);
    }, 60_000);

    return () => clearInterval(interval);
  }, [configured]);

  useEffect(() => {
    if (!configured) return;

    refreshSnapshots(symbols).catch(() => undefined);

    const interval = setInterval(() => {
      refreshSnapshots(symbols).catch(() => undefined);
    }, 30_000);

    return () => clearInterval(interval);
  }, [configured, symbols, refreshSnapshots]);

  useEffect(() => {
    if (!configured) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    refreshBars(activeSymbol, timeframe)
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [configured, activeSymbol, timeframe, refreshBars]);

  function handleAddSymbol(symbol: string) {
    if (symbols.includes(symbol)) {
      setActiveSymbol(symbol);
      return;
    }
    setSymbols((prev) => [...prev, symbol]);
    setActiveSymbol(symbol);
  }

  const activeSnapshot = snapshots[activeSymbol];
  const price =
    activeSnapshot?.latestTrade?.p ??
    activeSnapshot?.dailyBar?.c ??
    activeSnapshot?.latestQuote?.ap;
  const prevClose = activeSnapshot?.prevDailyBar?.c;
  const change =
    price !== undefined && prevClose !== undefined ? price - prevClose : null;
  const changePct =
    change !== null && prevClose !== undefined && prevClose !== 0
      ? (change / prevClose) * 100
      : null;
  const changeClass =
    change === null ? "" : change >= 0 ? "positive" : "negative";

  const recentBars = [...bars].reverse().slice(0, 12);

  return (
    <>
      <header className="top-bar">
        <div className="brand">
          <span className="brand-name">MarketPulse</span>
          <span className="brand-tag">Market Data</span>
        </div>
        {configured !== null && (
          <span
            className={`status-pill ${configured ? "connected" : "disconnected"}`}
          >
            {configured ? "Alpaca connected" : "Alpaca not configured"}
          </span>
        )}
      </header>

      <div className="dashboard">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2 className="sidebar-title">Watchlist</h2>
            <SymbolSearch onSelect={handleAddSymbol} />
          </div>
          <Watchlist
            symbols={symbols}
            activeSymbol={activeSymbol}
            snapshots={snapshots}
            onSelect={setActiveSymbol}
          />
        </aside>

        <main className="main-panel">
          {configured === false && (
            <div className="setup-banner">
              <h3>Connect Alpaca to load market data</h3>
              <p>
                Copy <code>backend/.env.example</code> to <code>backend/.env</code>{" "}
                and add your Alpaca API key and secret. Restart the backend, then
                refresh this page.
              </p>
            </div>
          )}

          {error && <div className="error-banner">{error}</div>}

          {syncStatus && !syncStatus.backfill_complete && (
            <div className="sync-banner">
              Syncing historical data — {syncStatus.sync_jobs_complete.toLocaleString()} /{" "}
              {syncStatus.sync_jobs_total.toLocaleString()} jobs complete (
              {syncStatus.symbols_total.toLocaleString()} symbols). Charts use data as it
              arrives.
            </div>
          )}

          <div className="symbol-header">
            <div className="symbol-identity">
              <h1>{activeSymbol}</h1>
              <div className="symbol-meta">
                {loading ? "Updating…" : "US Equity · IEX feed"}
              </div>
            </div>
            <div className="price-block">
              <div className="price-value">{formatPrice(price)}</div>
              {change !== null && changePct !== null && (
                <div className={`price-change ${changeClass}`}>
                  {change >= 0 ? "+" : ""}
                  {change.toFixed(2)} ({changePct >= 0 ? "+" : ""}
                  {changePct.toFixed(2)}%)
                </div>
              )}
            </div>
          </div>

          <div className="stats-row">
            <div className="stat">
              <span className="stat-label">Open</span>
              <span className="stat-value">
                {formatPrice(activeSnapshot?.dailyBar?.o)}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">High</span>
              <span className="stat-value">
                {formatPrice(activeSnapshot?.dailyBar?.h)}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Low</span>
              <span className="stat-value">
                {formatPrice(activeSnapshot?.dailyBar?.l)}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Volume</span>
              <span className="stat-value">
                {formatVolume(activeSnapshot?.dailyBar?.v)}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Prev Close</span>
              <span className="stat-value">{formatPrice(prevClose)}</span>
            </div>
          </div>

          <section className="chart-section">
            {bars.length > 0 ? (
              <PriceChart bars={bars} symbol={activeSymbol} timeframe={timeframe.value} />
            ) : (
              <div className="empty-state">
                {loading
                  ? "Loading chart data…"
                  : configured
                    ? "No chart data for this timeframe"
                    : "No chart data available"}
              </div>
            )}
          </section>

          <div className="timeframe-bar">
            {TIMEFRAMES.map((tf, idx) => (
              <button
                key={tf.value}
                type="button"
                className={`timeframe-btn${idx === timeframeIdx ? " active" : ""}`}
                onClick={() => setTimeframeIdx(idx)}
              >
                {tf.label}
              </button>
            ))}
          </div>

          <div className="bars-table-wrap">
            <table className="bars-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Open</th>
                  <th>High</th>
                  <th>Low</th>
                  <th>Close</th>
                  <th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {recentBars.map((bar) => (
                  <tr key={bar.t}>
                    <td>{formatDate(bar.t)}</td>
                    <td>{bar.o.toFixed(2)}</td>
                    <td>{bar.h.toFixed(2)}</td>
                    <td>{bar.l.toFixed(2)}</td>
                    <td>{bar.c.toFixed(2)}</td>
                    <td>{formatVolume(bar.v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </>
  );
}
