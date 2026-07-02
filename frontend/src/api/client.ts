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

export interface SyncStatus {
  symbols_total: number;
  sync_jobs_total: number;
  sync_jobs_complete: number;
  backfill_complete: boolean;
  bar_counts: Record<string, number>;
  last_error: string | null;
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
  options?: { start?: string; limit?: number },
): Promise<AlpacaBar[]> {
  const params = new URLSearchParams({ symbol, timeframe });
  if (options?.start) params.set("start", options.start);
  if (options?.limit) params.set("limit", String(options.limit));
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

export async function getSyncStatus(): Promise<SyncStatus> {
  const res = await apiFetch("/api/market/sync/status");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to fetch sync status");
  }
  return res.json();
}
