from fastapi import APIRouter, HTTPException, Query

from app.alpaca import alpaca_client

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/status")
async def market_status() -> dict:
    from app.config import settings

    return {
        "configured": bool(settings.alpaca_api_key and settings.alpaca_api_secret),
    }


@router.get("/snapshots")
async def snapshots(symbols: str = Query(..., description="Comma-separated symbols")) -> dict:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol is required")

    try:
        return await alpaca_client.get_snapshots(symbol_list)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca request failed: {exc}") from exc


@router.get("/bars")
async def bars(
    symbol: str = Query(..., min_length=1),
    timeframe: str = Query("1Day"),
    limit: int = Query(100, ge=1, le=1000),
    start: str | None = None,
    end: str | None = None,
) -> dict:
    try:
        return await alpaca_client.get_bars(
            symbol=symbol.upper(),
            timeframe=timeframe,
            limit=limit,
            start=start,
            end=end,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca request failed: {exc}") from exc


@router.get("/search")
async def search(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)) -> dict:
    try:
        results = await alpaca_client.search_assets(q, limit=limit)
        return {"results": results}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca request failed: {exc}") from exc


@router.get("/quote/{symbol}")
async def quote(symbol: str) -> dict:
    try:
        return await alpaca_client.get_latest_quote(symbol.upper())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Alpaca request failed: {exc}") from exc
