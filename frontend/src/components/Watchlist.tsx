import type { AlpacaSnapshot } from "../api/client";

interface WatchlistProps {
  symbols: string[];
  activeSymbol: string;
  snapshots: Record<string, AlpacaSnapshot>;
  onSelect: (symbol: string) => void;
}

function formatPrice(value: number | undefined): string {
  if (value === undefined) return "—";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function getChange(snapshot: AlpacaSnapshot | undefined): {
  value: number;
  pct: number;
} | null {
  if (!snapshot?.dailyBar || !snapshot?.prevDailyBar) return null;
  const current = snapshot.dailyBar.c;
  const previous = snapshot.prevDailyBar.c;
  const value = current - previous;
  const pct = previous !== 0 ? (value / previous) * 100 : 0;
  return { value, pct };
}

export function Watchlist({
  symbols,
  activeSymbol,
  snapshots,
  onSelect,
}: WatchlistProps) {
  return (
    <div className="watchlist">
      {symbols.map((symbol) => {
        const snapshot = snapshots[symbol];
        const price =
          snapshot?.latestTrade?.p ??
          snapshot?.dailyBar?.c ??
          snapshot?.latestQuote?.ap;
        const change = getChange(snapshot);
        const changeClass =
          change === null ? "" : change.value >= 0 ? "positive" : "negative";

        return (
          <button
            key={symbol}
            type="button"
            className={`watchlist-item${symbol === activeSymbol ? " active" : ""}`}
            onClick={() => onSelect(symbol)}
          >
            <span className="watchlist-symbol">{symbol}</span>
            <span className="watchlist-price">{formatPrice(price)}</span>
            {change && (
              <span className={`watchlist-change ${changeClass}`}>
                {change.value >= 0 ? "+" : ""}
                {change.value.toFixed(2)} ({change.pct >= 0 ? "+" : ""}
                {change.pct.toFixed(2)}%)
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
