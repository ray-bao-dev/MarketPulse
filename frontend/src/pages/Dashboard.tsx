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
import { ChartToolbar } from "../components/ChartToolbar";
import { PriceChart } from "../components/PriceChart";
import { SymbolSearch } from "../components/SymbolSearch";
import { Watchlist } from "../components/Watchlist";

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"];
const TIMEFRAMES = [
  {
    label: "1H",
    value: "1Hour",
    lookbackDays: 5,
    visibleBars: 40,
    rangeLabel: "Last 5 days",
  },
  {
    label: "1D",
    value: "1Day",
    lookbackDays: 180,
    visibleBars: 120,
    rangeLabel: "Last 6 months",
  },
  {
    label: "1W",
    value: "1Week",
    lookbackDays: 730,
    visibleBars: 104,
    rangeLabel: "Last 2 years",
  },
] as const;

function lookbackStartDate(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

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

function useHistoryOpenDefault(): [boolean, (value: boolean | ((prev: boolean) => boolean)) => void] {
  const [open, setOpen] = useState(() => window.matchMedia("(min-width: 1100px)").matches);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1100px)");
    const handler = (e: MediaQueryListEvent) => setOpen(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return [open, setOpen];
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
  const [historyOpen, setHistoryOpen] = useHistoryOpenDefault();

  const timeframe = TIMEFRAMES[timeframeIdx];

  const refreshSnapshots = useCallback(async (symbolList: string[]) => {
    const data = await getSnapshots(symbolList);
    setSnapshots(data);
  }, []);

  const refreshBars = useCallback(
    async (symbol: string, tf: (typeof TIMEFRAMES)[number]) => {
      const data = await getBars(symbol, tf.value, {
        start: lookbackStartDate(tf.lookbackDays),
      });
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

  const syncPct =
    syncStatus && syncStatus.sync_jobs_total > 0
      ? Math.round(
          (syncStatus.sync_jobs_complete / syncStatus.sync_jobs_total) * 100,
        )
      : null;

  const showSync =
    syncStatus &&
    !syncStatus.backfill_complete &&
    syncStatus.sync_jobs_total > 0;

  return (
    <>
      <header className="top-bar">
        <div className="brand">
          <span className="brand-name">MarketPulse</span>
          <span className="brand-tag">Market Data</span>
        </div>
        <div className="status-cluster">
          {configured !== null && (
            <span
              className={`status-item${configured ? " live" : " offline"}`}
              title={configured ? "Alpaca connected" : "Alpaca not configured"}
            >
              <span className="status-dot" />
              {configured ? "Live" : "Offline"}
            </span>
          )}
          {showSync && syncPct !== null && (
            <span className="status-item syncing" title="Historical data sync">
              <span className="status-dot" />
              Sync {syncPct}%
            </span>
          )}
        </div>
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

          <section className="quote-strip">
            <div className="quote-strip-top">
              <div className="symbol-identity">
                <h1>{activeSymbol}</h1>
                <div className="symbol-meta">
                  {loading ? "Updating…" : "US Equity · IEX feed"}
                </div>
              </div>
              <div className="price-block">
                <div className={`price-value mono-data${loading ? " loading-shimmer" : ""}`}>
                  {formatPrice(price)}
                </div>
                {change !== null && changePct !== null && (
                  <div className={`price-change mono-data ${changeClass}`}>
                    {change >= 0 ? "+" : ""}
                    {change.toFixed(2)} ({changePct >= 0 ? "+" : ""}
                    {changePct.toFixed(2)}%)
                  </div>
                )}
              </div>
            </div>
            <div className="quote-strip-stats">
              <div className="stat">
                <span className="stat-label">Open</span>
                <span className="stat-value mono-data">
                  {formatPrice(activeSnapshot?.dailyBar?.o)}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">High</span>
                <span className="stat-value mono-data">
                  {formatPrice(activeSnapshot?.dailyBar?.h)}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Low</span>
                <span className="stat-value mono-data">
                  {formatPrice(activeSnapshot?.dailyBar?.l)}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Volume</span>
                <span className="stat-value mono-data">
                  {formatVolume(activeSnapshot?.dailyBar?.v)}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Prev Close</span>
                <span className="stat-value mono-data">{formatPrice(prevClose)}</span>
              </div>
            </div>
          </section>

          <section className="chart-card">
            <ChartToolbar
              timeframes={TIMEFRAMES}
              activeIdx={timeframeIdx}
              onSelect={setTimeframeIdx}
            />
            <div className="chart-card-body">
              {bars.length > 0 ? (
                <PriceChart
                  bars={bars}
                  symbol={activeSymbol}
                  timeframe={timeframe.value}
                  visibleBars={timeframe.visibleBars}
                />
              ) : loading ? (
                <div className="chart-skeleton" aria-label="Loading chart data" />
              ) : (
                <div className="empty-state">
                  {configured
                    ? "No chart data for this timeframe"
                    : "No chart data available"}
                </div>
              )}
            </div>
          </section>

          <section className="history-section">
            <button
              type="button"
              className="history-toggle"
              onClick={() => setHistoryOpen((v) => !v)}
              aria-expanded={historyOpen}
            >
              <span>Recent bars</span>
              <span className="history-toggle-icon">{historyOpen ? "−" : "+"}</span>
            </button>
            {historyOpen && (
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
                    {recentBars.map((bar, idx) => {
                      const prevCloseBar =
                        idx < recentBars.length - 1
                          ? recentBars[idx + 1].c
                          : null;
                      const closeClass =
                        prevCloseBar === null
                          ? ""
                          : bar.c >= prevCloseBar
                            ? "positive"
                            : "negative";
                      return (
                        <tr key={bar.t}>
                          <td>{formatDate(bar.t)}</td>
                          <td className="mono-data">{bar.o.toFixed(2)}</td>
                          <td className="mono-data">{bar.h.toFixed(2)}</td>
                          <td className="mono-data">{bar.l.toFixed(2)}</td>
                          <td className={`mono-data ${closeClass}`}>
                            {bar.c.toFixed(2)}
                          </td>
                          <td className="mono-data">{formatVolume(bar.v)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
      </div>
    </>
  );
}
