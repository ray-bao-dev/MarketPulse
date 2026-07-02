interface ChartToolbarProps {
  timeframes: readonly { label: string; value: string; rangeLabel: string }[];
  activeIdx: number;
  onSelect: (idx: number) => void;
}

export function ChartToolbar({
  timeframes,
  activeIdx,
  onSelect,
}: ChartToolbarProps) {
  const active = timeframes[activeIdx];

  return (
    <div className="chart-toolbar">
      <div className="segmented-control" role="tablist" aria-label="Chart timeframe">
        {timeframes.map((tf, idx) => (
          <button
            key={tf.value}
            type="button"
            role="tab"
            aria-selected={idx === activeIdx}
            className={`segment${idx === activeIdx ? " active" : ""}`}
            onClick={() => onSelect(idx)}
          >
            {tf.label}
          </button>
        ))}
      </div>
      <span className="chart-toolbar-label">
        {active.rangeLabel} · {active.label.toLowerCase()} bars
      </span>
    </div>
  );
}
