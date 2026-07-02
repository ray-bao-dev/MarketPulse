import { createChart, ColorType, IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { AlpacaBar } from "../api/client";

const CHART_BG = "#18181b";
const GRID_COLOR = "#27272a";

interface PriceChartProps {
  bars: AlpacaBar[];
  symbol: string;
  timeframe: string;
  visibleBars: number;
}

function toChartTime(bar: AlpacaBar, timeframe: string): Time {
  const isIntraday = /hour|min|t$/i.test(timeframe);
  if (isIntraday) {
    return Math.floor(new Date(bar.t).getTime() / 1000) as Time;
  }
  return bar.t.slice(0, 10) as Time;
}

export function PriceChart({ bars, symbol, timeframe, visibleBars }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: CHART_BG },
        textColor: "#71717a",
        fontFamily: '"IBM Plex Mono", monospace',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: GRID_COLOR },
        horzLines: { color: GRID_COLOR },
      },
      crosshair: {
        vertLine: { color: "#52525b", labelBackgroundColor: "#27272a" },
        horzLine: { color: "#52525b", labelBackgroundColor: "#27272a" },
      },
      rightPriceScale: {
        borderColor: GRID_COLOR,
      },
      handleScroll: {
        mouseWheel: false,
        pressedMouseMove: false,
        horzTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: { time: false, price: true },
        mouseWheel: false,
        pinch: false,
      },
      timeScale: {
        borderColor: GRID_COLOR,
        timeVisible: true,
        fixLeftEdge: true,
        fixRightEdge: true,
        minimumHeight: 0,
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
    if (!seriesRef.current || !chartRef.current) return;

    const data = bars.map((bar) => ({
      time: toChartTime(bar, timeframe),
      open: bar.o,
      high: bar.h,
      low: bar.l,
      close: bar.c,
    }));

    seriesRef.current.setData(data);

    const visible = Math.min(visibleBars, data.length);
    if (visible > 0) {
      chartRef.current.timeScale().setVisibleLogicalRange({
        from: data.length - visible,
        to: data.length - 1,
      });
    }
  }, [bars, symbol, timeframe, visibleBars]);

  return <div ref={containerRef} className="chart-container" />;
}
