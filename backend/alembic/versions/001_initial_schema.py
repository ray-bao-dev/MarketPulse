"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "symbols",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.create_table(
        "bars",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("vwap", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("trade_count", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("symbol", "timeframe", "ts"),
    )
    op.create_index(
        "ix_bars_symbol_timeframe_ts",
        "bars",
        ["symbol", "timeframe", sa.text("ts DESC")],
    )
    op.create_table(
        "sync_state",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("backfill_complete", sa.Boolean(), nullable=False),
        sa.Column("oldest_bar_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("newest_bar_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("symbol", "timeframe"),
    )
    op.create_index(
        "ix_sync_state_backfill",
        "sync_state",
        ["backfill_complete", "symbol", "timeframe"],
    )


def downgrade() -> None:
    op.drop_index("ix_sync_state_backfill", table_name="sync_state")
    op.drop_table("sync_state")
    op.drop_index("ix_bars_symbol_timeframe_ts", table_name="bars")
    op.drop_table("bars")
    op.drop_table("symbols")
