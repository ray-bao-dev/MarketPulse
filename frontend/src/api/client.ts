export interface AlpacaBar {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
  vw?: number;
  n?: number;
}

export interface AlpacaSnapshot {
  latestTrade?: { p: number; s: number; t: string };
  latestQuote?: { ap: number; bp: number; as: number; bs: number; t: string };
  minuteBar?: AlpacaBar;
  dailyBar?: AlpacaBar;
  prevDailyBar?: AlpacaBar;
}

export interface AssetSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  tradable: boolean;
}

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

async function apiFetch(path: string): Promise<Response> {
  return fetch(`${API_BASE}${path}`);
}

export async function getMarketStatus(): Promise<{ configured: boolean }> {
  const res = await apiFetch("/api/market/status");
  if (!res.ok) throw new Error("Failed to check API status");
  return res.json();
}

export async function getSnapshots(
  symbols: string[],
): Promise<Record<string, AlpacaSnapshot>> {
  const res = await apiFetch(`/api/market/snapshots?symbols=${symbols.join(",")}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to fetch snapshots");
  }
  const data = await res.json();
  return data.snapshots ?? {};
}

export async function getBars(
  symbol: string,
  timeframe: string,
  limit: number,
): Promise<AlpacaBar[]> {
  const params = new URLSearchParams({
    symbol,
    timeframe,
    limit: String(limit),
  });
  const res = await apiFetch(`/api/market/bars?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to fetch bars");
  }
  const data = await res.json();
  return data.bars?.[symbol] ?? [];
}

export async function searchAssets(query: string): Promise<AssetSearchResult[]> {
  const params = new URLSearchParams({ q: query, limit: "8" });
  const res = await apiFetch(`/api/market/search?${params}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Search failed");
  }
  const data = await res.json();
  return data.results ?? [];
}
