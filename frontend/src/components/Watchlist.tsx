import type { AlpacaSnapshot } from "../api/client";

interface WatchlistProps {
  symbols: string[];
  activeSymbol: string;
  snapshots: Record<string, AlpacaSnapshot>;
  onSelect: (symbol: string) => void;
  onRemove: (symbol: string) => void;
}

function formatPrice(value: number | undefined): string {
  if (value === undefined) return "—";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function getChangePct(snapshot: AlpacaSnapshot | undefined): number | null {
  if (!snapshot?.dailyBar || !snapshot?.prevDailyBar) return null;
  const current = snapshot.dailyBar.c;
  const previous = snapshot.prevDailyBar.c;
  if (previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

export function Watchlist({
  symbols,
  activeSymbol,
  snapshots,
  onSelect,
  onRemove,
}: WatchlistProps) {
  const canRemove = symbols.length > 1;

  return (
    <div className="watchlist">
      {symbols.map((symbol) => {
        const snapshot = snapshots[symbol];
        const price =
          snapshot?.latestTrade?.p ??
          snapshot?.dailyBar?.c ??
          snapshot?.latestQuote?.ap;
        const changePct = getChangePct(snapshot);
        const changeClass =
          changePct === null ? "" : changePct >= 0 ? "positive" : "negative";

        return (
          <div
            key={symbol}
            className={`watchlist-item${symbol === activeSymbol ? " active" : ""}`}
          >
            <button
              type="button"
              className="watchlist-select"
              onClick={() => onSelect(symbol)}
            >
              <span className="watchlist-symbol">{symbol}</span>
              <span className="watchlist-price mono-data">{formatPrice(price)}</span>
              {changePct !== null && (
                <span className={`watchlist-change mono-data ${changeClass}`}>
                  {changePct >= 0 ? "+" : ""}
                  {changePct.toFixed(2)}%
                </span>
              )}
            </button>
            {canRemove && (
              <button
                type="button"
                className="watchlist-remove"
                aria-label={`Remove ${symbol} from watchlist`}
                title={`Remove ${symbol}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(symbol);
                }}
              >
                ×
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
