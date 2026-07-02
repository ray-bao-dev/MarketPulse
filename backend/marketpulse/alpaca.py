import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from marketpulse.config import settings


def _default_start(timeframe: str, limit: int) -> str:
    now = datetime.now(timezone.utc)
    tf = timeframe.lower()

    if tf in ("1hour", "1h") or tf.endswith("hour") or tf.endswith("h"):
        delta = timedelta(hours=limit * 3)
    elif "min" in tf:
        # ~78 five-minute bars per regular US session
        delta = timedelta(days=max(5, int(limit / 60) + 3))
    elif tf in ("1week", "1w") or tf.endswith("week") or tf.endswith("w"):
        delta = timedelta(weeks=limit + 8)
    elif tf in ("1day", "1d") or tf.endswith("day") or tf.endswith("d"):
        delta = timedelta(days=int(limit * 1.45))
    else:
        delta = timedelta(days=limit)

    return (now - delta).date().isoformat()


def parse_alpaca_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


class AlpacaClient:
    def __init__(self) -> None:
        self._headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
        }
        self._client: httpx.AsyncClient | None = None
        self._assets_cache: tuple[float, list[dict[str, Any]]] | None = None

    def _configured(self) -> bool:
        return bool(settings.alpaca_api_key and settings.alpaca_api_secret)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def _get(self, base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self._configured():
            raise RuntimeError("Alpaca API credentials are not configured")

        client = await self._get_client()
        response = await client.get(
            f"{base_url}{path}",
            headers=self._headers,
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def get_snapshots(self, symbols: list[str]) -> dict[str, Any]:
        data = await self._get(
            settings.alpaca_data_base_url,
            "/v2/stocks/snapshots",
            {"symbols": ",".join(symbols), "feed": "iex"},
        )
        return data.get("snapshots", data)

    async def get_bars_page(
        self,
        symbol: str,
        timeframe: str,
        *,
        start: str | None = None,
        end: str | None = None,
        limit: int = 10000,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbols": symbol,
            "timeframe": timeframe,
            "limit": min(limit, 10000),
            "feed": "iex",
            "adjustment": "split",
            "sort": "asc",
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if page_token:
            params["page_token"] = page_token

        return await self._get(settings.alpaca_data_base_url, "/v2/stocks/bars", params)

    async def iter_all_bars(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str | None = None,
        *,
        throttle_seconds: float = 0.2,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        page_token: str | None = None
        while True:
            payload = await self.get_bars_page(
                symbol,
                timeframe,
                start=start,
                end=end,
                page_token=page_token,
            )
            bars = payload.get("bars", {}).get(symbol, [])
            if bars:
                yield bars

            page_token = payload.get("next_page_token")
            if not page_token:
                break
            await asyncio.sleep(throttle_seconds)

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        if not start:
            start = _default_start(timeframe, limit)
        return await self.get_bars_page(symbol, timeframe, start=start, end=end, limit=limit)

    async def list_assets(self) -> list[dict[str, Any]]:
        import time

        cache_ttl = 3600.0
        now = time.monotonic()
        if self._assets_cache and now - self._assets_cache[0] < cache_ttl:
            return self._assets_cache[1]

        assets = await self._get(
            settings.alpaca_trading_base_url,
            "/v2/assets",
            {"status": "active", "asset_class": "us_equity"},
        )
        self._assets_cache = (now, assets)
        return assets

    async def search_assets(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        assets = await self.list_assets()
        needle = query.upper()
        matches = [
            asset
            for asset in assets
            if needle in asset.get("symbol", "").upper()
            or needle in asset.get("name", "").upper()
        ]
        return matches[:limit]

    async def get_latest_quote(self, symbol: str) -> dict[str, Any]:
        return await self._get(
            settings.alpaca_data_base_url,
            f"/v2/stocks/{symbol}/quotes/latest",
            {"feed": "iex"},
        )


alpaca_client = AlpacaClient()
