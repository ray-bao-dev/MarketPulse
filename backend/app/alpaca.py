from typing import Any

import httpx

from app.config import settings


class AlpacaClient:
    def __init__(self) -> None:
        self._headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
        }

    def _configured(self) -> bool:
        return bool(settings.alpaca_api_key and settings.alpaca_api_secret)

    async def _get(self, base_url: str, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self._configured():
            raise RuntimeError("Alpaca API credentials are not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}{path}",
                headers=self._headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_snapshots(self, symbols: list[str]) -> dict[str, Any]:
        return await self._get(
            settings.alpaca_data_base_url,
            "/v2/stocks/snapshots",
            {"symbols": ",".join(symbols), "feed": "iex"},
        )

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbols": symbol,
            "timeframe": timeframe,
            "limit": limit,
            "feed": "iex",
            "adjustment": "split",
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        return await self._get(settings.alpaca_data_base_url, "/v2/stocks/bars", params)

    async def search_assets(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        assets = await self._get(
            settings.alpaca_trading_base_url,
            "/v2/assets",
            {"status": "active", "asset_class": "us_equity"},
        )
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
