import type { SeriesMarker, Time } from "lightweight-charts";
import type { PatternDetection } from "../api/client";

const LABEL_COLORS: Record<string, string> = {
  hammer: "#34d399",
  doji: "#f59e0b",
  bullish_engulfing: "#34d399",
  bearish_engulfing: "#f87171",
  shooting_star: "#f87171",
  morning_star: "#34d399",
};

function toChartTime(iso: string, timeframe: string): Time {
  const isIntraday = /hour|min|t$/i.test(timeframe);
  if (isIntraday) {
    return Math.floor(new Date(iso).getTime() / 1000) as Time;
  }
  return iso.slice(0, 10) as Time;
}

function formatLabel(label: string): string {
  return label.replace(/_/g, " ");
}

export function patternsToMarkers(
  patterns: PatternDetection[],
  timeframe: string,
): SeriesMarker<Time>[] {
  return patterns.map((pattern) => {
    const bullish = pattern.direction === "bullish";
    const bearish = pattern.direction === "bearish";
    return {
      time: toChartTime(pattern.t, timeframe),
      position: bullish ? "belowBar" : bearish ? "aboveBar" : "inBar",
      color: LABEL_COLORS[pattern.label] ?? "#f59e0b",
      shape: bullish ? "arrowUp" : bearish ? "arrowDown" : "circle",
      text: `${formatLabel(pattern.label)} ${(pattern.confidence * 100).toFixed(0)}%`,
    };
  });
}

export interface PatternSummary {
  label: string;
  count: number;
  avgConfidence: number;
  direction: string;
}

export function summarizePatterns(patterns: PatternDetection[]): PatternSummary[] {
  const map = new Map<string, { count: number; total: number; direction: string }>();

  for (const pattern of patterns) {
    const entry = map.get(pattern.label) ?? {
      count: 0,
      total: 0,
      direction: pattern.direction,
    };
    entry.count += 1;
    entry.total += pattern.confidence;
    map.set(pattern.label, entry);
  }

  return Array.from(map.entries())
    .map(([label, entry]) => ({
      label,
      count: entry.count,
      avgConfidence: entry.total / entry.count,
      direction: entry.direction,
    }))
    .sort((a, b) => b.count - a.count);
}
