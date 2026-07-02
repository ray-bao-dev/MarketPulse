import { summarizePatterns } from "./PatternLegend";
import type { PatternDetection } from "../api/client";

interface PatternLegendProps {
  patterns: PatternDetection[];
  modelVersion?: string | null;
  inferenceMode?: string | null;
}

function formatLabel(label: string): string {
  return label.replace(/_/g, " ");
}

export function PatternLegendPanel({
  patterns,
  modelVersion,
  inferenceMode,
}: PatternLegendProps) {
  const summary = summarizePatterns(patterns);

  if (summary.length === 0) {
    return (
      <div className="pattern-legend empty">
        <p>No patterns detected above the confidence threshold.</p>
      </div>
    );
  }

  return (
    <div className="pattern-legend">
      <div className="pattern-legend-header">
        <h3>Detected patterns</h3>
        {(modelVersion || inferenceMode) && (
          <span className="pattern-legend-meta">
            {modelVersion && <>Model {modelVersion}</>}
            {modelVersion && inferenceMode && " · "}
            {inferenceMode && <>{inferenceMode}</>}
          </span>
        )}
      </div>
      <div className="pattern-legend-grid">
        {summary.map((item) => (
          <div key={item.label} className={`pattern-legend-item ${item.direction}`}>
            <span className="pattern-legend-label">{formatLabel(item.label)}</span>
            <span className="pattern-legend-stats mono-data">
              {item.count} · {(item.avgConfidence * 100).toFixed(0)}% avg
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
