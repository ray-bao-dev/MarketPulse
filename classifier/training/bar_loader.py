"""Load OHLCV bars from JSON exports or PostgreSQL."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Bar:
    t: str
    o: float
    h: float
    l: float
    c: float
    v: int


def load_bars_json(path: Path) -> list[Bar]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_bars = payload.get("bars", payload)
    if isinstance(raw_bars, dict):
        raw_bars = next(iter(raw_bars.values()))
    return [_bar_from_dict(item) for item in raw_bars]


def _bar_from_dict(item: dict) -> Bar:
    return Bar(
        t=item["t"],
        o=float(item["o"]),
        h=float(item["h"]),
        l=float(item["l"]),
        c=float(item["c"]),
        v=int(item.get("v", 0)),
    )


def _sync_database_url(database_url: str) -> str:
    url = database_url.strip()
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def load_bars_db(
    *,
    database_url: str,
    symbol: str,
    timeframe: str,
    start: str | None = None,
    end: str | None = None,
) -> list[Bar]:
    from sqlalchemy import create_engine, text

    engine = create_engine(_sync_database_url(database_url))
    query = """
        SELECT ts, open, high, low, close, volume
        FROM bars
        WHERE symbol = :symbol AND timeframe = :timeframe
    """
    params: dict[str, object] = {"symbol": symbol.upper(), "timeframe": timeframe}

    if start:
        query += " AND ts >= :start"
        params["start"] = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if end:
        query += " AND ts <= :end"
        params["end"] = datetime.fromisoformat(end.replace("Z", "+00:00"))

    query += " ORDER BY ts ASC"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        Bar(
            t=row.ts.isoformat().replace("+00:00", "Z"),
            o=float(row.open),
            h=float(row.high),
            l=float(row.low),
            c=float(row.close),
            v=int(row.volume),
        )
        for row in rows
    ]


def load_bars_multi(
    *,
    database_url: str | None,
    json_paths: list[Path],
    symbols: list[str],
    timeframe: str,
    start: str | None,
    end: str | None,
) -> list[Bar]:
    if json_paths:
        bars: list[Bar] = []
        for path in json_paths:
            bars.extend(load_bars_json(path))
        return sorted(bars, key=lambda b: b.t)

    if not database_url:
        raise ValueError("Provide --bars JSON file(s) or --database-url with --symbols")

    bars = []
    for symbol in symbols:
        bars.extend(
            load_bars_db(
                database_url=database_url,
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
        )
    return sorted(bars, key=lambda b: b.t)
