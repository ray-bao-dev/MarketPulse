from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.alpaca import alpaca_client
from marketpulse.config import settings
from marketpulse.db.session import get_db
from marketpulse.services.bars import (
    bar_to_api,
    get_sync_status,
    query_bars,
    search_symbols,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/status")
async def market_status() -> dict:
    return {
        "configured": bool(settings.alpaca_api_key and settings.alpaca_api_secret),
    }


@router.get("/sync/status")
async def sync_status(session: AsyncSession = Depends(get_db)) -> dict:
    try:
        return await get_sync_status(session)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("/snapshots")
async def snapshots(symbols: str = Query(..., description="Comma-separated symbols")) -> dict:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol is required")

    try:
        data = await alpaca_client.get_snapshots(symbol_list)
        return {"snapshots": data}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca request failed: {exc}") from exc


@router.get("/bars")
async def bars(
    symbol: str = Query(..., min_length=1),
    timeframe: str = Query("1Day"),
    limit: int | None = Query(None, ge=1, le=50000),
    start: str | None = None,
    end: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> dict:
    symbol = symbol.upper()
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    try:
        rows = await query_bars(
            session,
            symbol,
            timeframe,
            start=start_dt,
            end=end_dt,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    if not rows:
        try:
            payload = await alpaca_client.get_bars(
                symbol, timeframe, limit=limit or 10000, start=start, end=end
            )
            alpaca_bars = payload.get("bars", {}).get(symbol, [])
            return {"bars": {symbol: alpaca_bars}}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"No bars in database: {exc}") from exc

    return {"bars": {symbol: [bar_to_api(b) for b in rows]}}


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        results = await search_symbols(session, q, limit=limit)
        if results:
            return {
                "results": [
                    {
                        "symbol": s.symbol,
                        "name": s.name,
                        "exchange": s.exchange,
                        "tradable": s.is_active,
                    }
                    for s in results
                ]
            }
    except Exception:
        pass

    try:
        fallback = await alpaca_client.search_assets(q, limit=limit)
        return {"results": fallback}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc


@router.get("/quote/{symbol}")
async def quote(symbol: str) -> dict:
    try:
        return await alpaca_client.get_latest_quote(symbol.upper())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca request failed: {exc}") from exc
