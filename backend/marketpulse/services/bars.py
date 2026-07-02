from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from marketpulse.alpaca import parse_alpaca_ts
from marketpulse.config import settings
from marketpulse.db.models import Bar, Symbol, SyncState

# asyncpg/PostgreSQL limit is 32767 bind parameters per query
INSERT_BATCH_SIZE = 500


def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def alpaca_bar_to_row(symbol: str, timeframe: str, raw: dict) -> dict:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "ts": parse_alpaca_ts(raw["t"]),
        "open": raw["o"],
        "high": raw["h"],
        "low": raw["l"],
        "close": raw["c"],
        "volume": raw["v"],
        "vwap": raw.get("vw"),
        "trade_count": raw.get("n"),
    }


async def upsert_bars(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0

    inserted = 0
    for chunk in _batched(rows, INSERT_BATCH_SIZE):
        stmt = insert(Bar).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "timeframe", "ts"])
        result = await session.execute(stmt)
        inserted += result.rowcount or 0
    await session.commit()
    return inserted


async def query_bars(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[Bar]:
    if limit and not start and not end:
        stmt = (
            select(Bar)
            .where(Bar.symbol == symbol, Bar.timeframe == timeframe)
            .order_by(Bar.ts.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(reversed(result.scalars().all()))

    stmt = (
        select(Bar)
        .where(Bar.symbol == symbol, Bar.timeframe == timeframe)
        .order_by(Bar.ts.asc())
    )
    if start:
        stmt = stmt.where(Bar.ts >= start)
    if end:
        stmt = stmt.where(Bar.ts <= end)
    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


def bar_to_api(bar: Bar) -> dict:
    ts = bar.ts.isoformat().replace("+00:00", "Z")
    return {
        "t": ts,
        "o": float(bar.open),
        "h": float(bar.high),
        "l": float(bar.low),
        "c": float(bar.close),
        "v": int(bar.volume),
        "vw": float(bar.vwap) if bar.vwap is not None else None,
        "n": int(bar.trade_count) if bar.trade_count is not None else None,
    }


async def search_symbols(session: AsyncSession, query: str, limit: int = 10) -> list[Symbol]:
    pattern = f"%{query.upper()}%"
    stmt = (
        select(Symbol)
        .where(
            Symbol.is_active.is_(True),
            (Symbol.symbol.ilike(pattern) | Symbol.name.ilike(f"%{query}%")),
        )
        .order_by(Symbol.symbol)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def upsert_symbols(session: AsyncSession, assets: list[dict]) -> int:
    rows = [
        {
            "symbol": a["symbol"],
            "name": a.get("name", ""),
            "exchange": a.get("exchange", ""),
            "is_active": True,
        }
        for a in assets
        if a.get("symbol")
    ]
    if not rows:
        return 0

    total = 0
    for chunk in _batched(rows, INSERT_BATCH_SIZE):
        stmt = insert(Symbol).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": stmt.excluded.name,
                "exchange": stmt.excluded.exchange,
                "is_active": stmt.excluded.is_active,
            },
        )
        await session.execute(stmt)
        total += len(chunk)
    await session.commit()
    return total


async def ensure_sync_states_batch(
    session: AsyncSession, symbols: list[str], timeframes: list[str]
) -> None:
    rows = [
        {"symbol": symbol, "timeframe": timeframe, "backfill_complete": False}
        for symbol in symbols
        for timeframe in timeframes
    ]
    if not rows:
        return

    for chunk in _batched(rows, INSERT_BATCH_SIZE):
        stmt = insert(SyncState).values(chunk)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "timeframe"])
        await session.execute(stmt)
    await session.commit()


async def get_sync_state(
    session: AsyncSession, symbol: str, timeframe: str
) -> SyncState | None:
    result = await session.execute(
        select(SyncState).where(
            SyncState.symbol == symbol, SyncState.timeframe == timeframe
        )
    )
    return result.scalar_one_or_none()


async def ensure_sync_state(session: AsyncSession, symbol: str, timeframe: str) -> SyncState:
    state = await get_sync_state(session, symbol, timeframe)
    if state:
        return state
    state = SyncState(symbol=symbol, timeframe=timeframe, backfill_complete=False)
    session.add(state)
    await session.commit()
    await session.refresh(state)
    return state


async def update_sync_state(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    *,
    backfill_complete: bool | None = None,
    oldest_bar_ts: datetime | None = None,
    newest_bar_ts: datetime | None = None,
    last_error: str | None = None,
) -> None:
    state = await ensure_sync_state(session, symbol, timeframe)
    state.last_sync_at = datetime.now(timezone.utc)
    if backfill_complete is not None:
        state.backfill_complete = backfill_complete
    if oldest_bar_ts is not None:
        state.oldest_bar_ts = (
            oldest_bar_ts
            if state.oldest_bar_ts is None
            else min(state.oldest_bar_ts, oldest_bar_ts)
        )
    if newest_bar_ts is not None:
        state.newest_bar_ts = (
            newest_bar_ts
            if state.newest_bar_ts is None
            else max(state.newest_bar_ts, newest_bar_ts)
        )
    state.last_error = last_error
    await session.commit()


async def get_sync_status(session: AsyncSession) -> dict:
    total_symbols = await session.scalar(select(func.count()).select_from(Symbol))
    complete = await session.scalar(
        select(func.count())
        .select_from(SyncState)
        .where(SyncState.backfill_complete.is_(True))
    )
    total_jobs = await session.scalar(select(func.count()).select_from(SyncState))
    bar_counts: dict[str, int] = {}
    count_timeframes = list(settings.timeframe_list)
    for tf in settings.priority_intraday_timeframe_list:
        if tf not in count_timeframes:
            count_timeframes.append(tf)
    for tf in count_timeframes:
        count = await session.scalar(
            select(func.count()).select_from(Bar).where(Bar.timeframe == tf)
        )
        bar_counts[tf] = count or 0

    last_error = await session.scalar(
        select(SyncState.last_error)
        .where(SyncState.last_error.isnot(None))
        .order_by(SyncState.last_sync_at.desc())
        .limit(1)
    )

    return {
        "symbols_total": total_symbols or 0,
        "sync_jobs_total": total_jobs or 0,
        "sync_jobs_complete": complete or 0,
        "backfill_complete": (total_jobs or 0) > 0 and complete == total_jobs,
        "bar_counts": bar_counts,
        "last_error": last_error,
    }


async def pick_next_backfill_job(session: AsyncSession, priority: list[str]) -> tuple[str, str] | None:
    priority_timeframes = (
        settings.priority_intraday_timeframe_list + settings.timeframe_list
    )
    for symbol in priority:
        for timeframe in priority_timeframes:
            state = await get_sync_state(session, symbol, timeframe)
            if state is None or not state.backfill_complete:
                return symbol, timeframe

    stmt = (
        select(SyncState.symbol, SyncState.timeframe)
        .where(SyncState.backfill_complete.is_(False))
        .order_by(SyncState.last_sync_at.asc().nullsfirst())
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row:
        return row[0], row[1]

    stmt = (
        select(Symbol.symbol)
        .where(Symbol.is_active.is_(True))
        .order_by(Symbol.symbol)
        .limit(1)
    )
    symbol = await session.scalar(stmt)
    if symbol:
        return symbol, "1Day"
    return None
