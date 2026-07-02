import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { AlpacaBar } from "../api/client";

interface PriceChartProps {
  bars: AlpacaBar[];
  symbol: string;
}

export function PriceChart({ bars, symbol }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#09090b" },
        textColor: "#71717a",
        fontFamily: '"IBM Plex Mono", monospace',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1f1f23" },
        horzLines: { color: "#1f1f23" },
      },
      crosshair: {
        vertLine: { color: "#52525b", labelBackgroundColor: "#27272a" },
        horzLine: { color: "#52525b", labelBackgroundColor: "#27272a" },
      },
      rightPriceScale: {
        borderColor: "#27272a",
      },
      timeScale: {
        borderColor: "#27272a",
        timeVisible: true,
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#34d399",
      downColor: "#f87171",
      borderUpColor: "#34d399",
      borderDownColor: "#f87171",
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && chartRef.current) {
        chartRef.current.applyOptions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;

    const data = bars.map((bar) => ({
      time: (new Date(bar.t).getTime() / 1000) as unknown as string,
      open: bar.o,
      high: bar.h,
      low: bar.l,
      close: bar.c,
    }));

    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [bars, symbol]);

  return <div ref={containerRef} className="chart-container" />;
}
