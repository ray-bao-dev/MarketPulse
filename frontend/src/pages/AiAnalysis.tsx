import { useMemo, useState } from "react";
import { detectPatterns, type AlpacaBar, type PatternDetection } from "../api/client";
import { PatternLegendPanel } from "../components/PatternLegendPanel";
import { patternsToMarkers } from "../components/PatternLegend";
import { PriceChart } from "../components/PriceChart";
import { SymbolSearch } from "../components/SymbolSearch";

const TIMEFRAMES = [
  { label: "5M", value: "5Min" },
  { label: "1H", value: "1Hour" },
  { label: "1D", value: "1Day" },
] as const;

function defaultStartDate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 5);
  return date.toISOString().slice(0, 10);
}

function defaultEndDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function AiAnalysis() {
  const [symbol, setSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState<(typeof TIMEFRAMES)[number]["value"]>("5Min");
  const [start, setStart] = useState(defaultStartDate);
  const [end, setEnd] = useState(defaultEndDate);
  const [bars, setBars] = useState<AlpacaBar[]>([]);
  const [patterns, setPatterns] = useState<PatternDetection[]>([]);
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [inferenceMode, setInferenceMode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);

  const markers = useMemo(
    () => patternsToMarkers(patterns, timeframe),
    [patterns, timeframe],
  );

  async function handleAnalyze() {
    setLoading(true);
    setError(null);

    try {
      const result = await detectPatterns({ symbol, timeframe, start, end });
      setBars(result.bars);
      setPatterns(result.patterns);
      setModelVersion(result.model_version);
      setInferenceMode(result.inference_mode);
      setHasRun(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ai-analysis">
      <div className="ai-analysis-header">
        <div>
          <h1>AI Analysis</h1>
          <p className="ai-analysis-subtitle">
            Select a symbol and range, then run pattern detection on OHLCV bars.
          </p>
        </div>
      </div>

      <section className="ai-analysis-controls">
        <div className="ai-control">
          <label htmlFor="ai-symbol-search">Symbol</label>
          <div className="ai-symbol-row">
            <span className="ai-symbol-display mono-data">{symbol}</span>
            <SymbolSearch onSelect={setSymbol} />
          </div>
        </div>

        <div className="ai-control">
          <label htmlFor="ai-timeframe">Timeframe</label>
          <select
            id="ai-timeframe"
            className="ai-select"
            value={timeframe}
            onChange={(e) =>
              setTimeframe(e.target.value as (typeof TIMEFRAMES)[number]["value"])
            }
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf.value} value={tf.value}>
                {tf.label}
              </option>
            ))}
          </select>
        </div>

        <div className="ai-control">
          <label htmlFor="ai-start">Start</label>
          <input
            id="ai-start"
            className="ai-input mono-data"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </div>

        <div className="ai-control">
          <label htmlFor="ai-end">End</label>
          <input
            id="ai-end"
            className="ai-input mono-data"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </div>

        <button
          type="button"
          className="ai-analyze-btn"
          onClick={handleAnalyze}
          disabled={loading}
        >
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </section>

      {error && <div className="error-banner">{error}</div>}

      {hasRun && (
        <>
          <section className="ai-analysis-chart-card chart-card">
            <div className="chart-toolbar">
              <span className="chart-toolbar-label">
                {symbol} · {timeframe} · {start} to {end}
              </span>
              <span className="chart-toolbar-label">
                {patterns.length} pattern{patterns.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="chart-card-body">
              {bars.length > 0 ? (
                <PriceChart
                  bars={bars}
                  symbol={symbol}
                  timeframe={timeframe}
                  markers={markers}
                  fitAll
                />
              ) : (
                <div className="empty-state">No bars returned for this range.</div>
              )}
            </div>
          </section>

          <PatternLegendPanel
            patterns={patterns}
            modelVersion={modelVersion}
            inferenceMode={inferenceMode}
          />
        </>
      )}

      {!hasRun && !loading && (
        <div className="ai-analysis-body">
          <p className="ai-analysis-placeholder">
            Choose a symbol and date range, then click Analyze to detect candlestick
            patterns on the chart.
          </p>
        </div>
      )}
    </div>
  );
}
