import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from marketpulse.alpaca import alpaca_client
from marketpulse.config import settings
from marketpulse.db.models import Symbol, SyncState
from marketpulse.db.session import get_session_factory
from marketpulse.services.bars import (
    alpaca_bar_to_row,
    ensure_sync_state,
    pick_next_backfill_job,
    update_sync_state,
    upsert_bars,
    upsert_symbols,
)

logger = logging.getLogger(__name__)


async def bootstrap_symbols() -> int:
    assets = await alpaca_client.list_assets()
    factory = get_session_factory()
    async with factory() as session:
        count = await upsert_symbols(session, assets)
        for asset in assets:
            symbol = asset.get("symbol")
            if not symbol:
                continue
            for timeframe in settings.timeframe_list:
                await ensure_sync_state(session, symbol, timeframe)
    logger.info("Bootstrapped %s symbols (%s assets from Alpaca)", count, len(assets))
    return count


async def backfill_one(symbol: str, timeframe: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await ensure_sync_state(session, symbol, timeframe)

    start = settings.backfill_start_date
    total = 0

    async for page in alpaca_client.iter_all_bars(symbol, timeframe, start=start):
        rows = [alpaca_bar_to_row(symbol, timeframe, b) for b in page]
        async with factory() as session:
            await upsert_bars(session, rows)
        total += len(rows)

    async with factory() as session:
        oldest = newest = None
        if total > 0:
            from marketpulse.db.models import Bar

            result = await session.execute(
                select(Bar.ts)
                .where(Bar.symbol == symbol, Bar.timeframe == timeframe)
                .order_by(Bar.ts.asc())
                .limit(1)
            )
            oldest_row = result.scalar_one_or_none()
            result = await session.execute(
                select(Bar.ts)
                .where(Bar.symbol == symbol, Bar.timeframe == timeframe)
                .order_by(Bar.ts.desc())
                .limit(1)
            )
            newest_row = result.scalar_one_or_none()
            oldest = oldest_row
            newest = newest_row

        await update_sync_state(
            session,
            symbol,
            timeframe,
            backfill_complete=True,
            oldest_bar_ts=oldest,
            newest_bar_ts=newest,
            last_error=None,
        )

    logger.info("Backfilled %s %s: %s bars", symbol, timeframe, total)


async def incremental_sync(symbol: str, timeframe: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        state = await ensure_sync_state(session, symbol, timeframe)
        if not state.backfill_complete:
            return

        start = state.newest_bar_ts.isoformat() if state.newest_bar_ts else settings.backfill_start_date

    total = 0
    async for page in alpaca_client.iter_all_bars(symbol, timeframe, start=start):
        rows = [alpaca_bar_to_row(symbol, timeframe, b) for b in page]
        async with factory() as session:
            await upsert_bars(session, rows)
        total += len(rows)

    if total:
        async with factory() as session:
            from marketpulse.db.models import Bar

            newest = await session.scalar(
                select(Bar.ts)
                .where(Bar.symbol == symbol, Bar.timeframe == timeframe)
                .order_by(Bar.ts.desc())
                .limit(1)
            )
            await update_sync_state(
                session, symbol, timeframe, newest_bar_ts=newest, last_error=None
            )


async def run_backfill_loop() -> None:
    while True:
        factory = get_session_factory()
        async with factory() as session:
            job = await pick_next_backfill_job(session, settings.priority_symbol_list)

        if not job:
            logger.info("No backfill jobs pending")
            return

        symbol, timeframe = job
        try:
            await backfill_one(symbol, timeframe)
        except Exception as exc:
            logger.exception("Backfill failed for %s %s", symbol, timeframe)
            async with factory() as session:
                await update_sync_state(
                    session, symbol, timeframe, last_error=str(exc)
                )


async def run_incremental_sync() -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(SyncState.symbol, SyncState.timeframe).where(
                SyncState.backfill_complete.is_(True)
            )
        )
        jobs = list(result.all())

    for symbol, timeframe in jobs:
        try:
            await incremental_sync(symbol, timeframe)
        except Exception:
            logger.exception("Incremental sync failed for %s %s", symbol, timeframe)


async def run_worker() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Starting MarketPulse sync worker")

    await bootstrap_symbols()

    backfill_task = asyncio.create_task(_continuous_backfill())

    interval = settings.sync_interval_minutes * 60
    while True:
        await asyncio.sleep(interval)
        await run_incremental_sync()


async def _continuous_backfill() -> None:
    from sqlalchemy import func

    while True:
        factory = get_session_factory()
        async with factory() as session:
            pending = await session.scalar(
                select(func.count())
                .select_from(SyncState)
                .where(SyncState.backfill_complete.is_(False))
            )
        if not pending:
            logger.info("All backfill jobs complete")
            return

        await run_backfill_loop()
        await asyncio.sleep(1)
