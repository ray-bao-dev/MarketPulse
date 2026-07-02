from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.alpaca import alpaca_client
from marketpulse.config import settings
from marketpulse.db.session import get_db
from marketpulse.services.bars import bar_to_api, query_bars

router = APIRouter(prefix="/analysis", tags=["analysis"])


class DetectBody(BaseModel):
    symbol: str = Field(..., min_length=1)
    timeframe: str = Field(default="5Min")
    start: str = Field(..., description="ISO date or datetime")
    end: str | None = None


async def _fetch_bars(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    start: str,
    end: str | None,
) -> list[dict]:
    symbol = symbol.upper()
    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None

    rows = await query_bars(
        session,
        symbol,
        timeframe,
        start=start_dt,
        end=end_dt,
    )

    if rows:
        return [bar_to_api(b) for b in rows]

    try:
        payload = await alpaca_client.get_bars(
            symbol,
            timeframe,
            limit=10000,
            start=start[:10] if len(start) >= 10 else start,
            end=end[:10] if end and len(end) >= 10 else end,
        )
        return payload.get("bars", {}).get(symbol, [])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch bars: {exc}") from exc


@router.post("/detect")
async def detect_patterns(
    body: DetectBody,
    session: AsyncSession = Depends(get_db),
) -> dict:
    bars = await _fetch_bars(session, body.symbol, body.timeframe, body.start, body.end)
    if not bars:
        raise HTTPException(status_code=404, detail="No bars found for the selected range")

    classifier_url = settings.classifier_url.rstrip("/")
    payload = {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "bars": bars,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{classifier_url}/v1/detect", json=payload)
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Classifier error: {detail}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Classifier unavailable at {classifier_url}: {exc}",
        ) from exc

    return {
        "symbol": body.symbol.upper(),
        "timeframe": body.timeframe,
        "bars": bars,
        "patterns": result.get("patterns", []),
        "model_version": result.get("model_version"),
        "inference_mode": result.get("inference_mode"),
    }
