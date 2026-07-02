"""Rule-based pattern labelers for bootstrapping training data."""

from __future__ import annotations

from training.bar_loader import Bar


def _body(bar: Bar) -> float:
    return abs(bar.c - bar.o)


def _range(bar: Bar) -> float:
    return max(bar.h - bar.l, 1e-9)


def _upper_wick(bar: Bar) -> float:
    return bar.h - max(bar.o, bar.c)


def _lower_wick(bar: Bar) -> float:
    return min(bar.o, bar.c) - bar.l


def label_window(bars: list[Bar]) -> str:
    """Return pattern label for the last bar in window, or 'none'."""
    if len(bars) < 2:
        return "none"

    prev = bars[-2]
    bar = bars[-1]

    rng = _range(bar)
    body = _body(bar)

    if body / rng <= 0.35 and _lower_wick(bar) / rng >= 0.55 and _upper_wick(bar) / rng <= 0.15:
        if bar.c >= prev.c:
            return "hammer"

    if body / rng <= 0.12:
        return "doji"

    if prev.c < prev.o and bar.c > bar.o and bar.o <= prev.c and bar.c >= prev.o:
        return "bullish_engulfing"

    if prev.c > prev.o and bar.c < bar.o and bar.o >= prev.c and bar.c <= prev.o:
        return "bearish_engulfing"

    if body / rng <= 0.35 and _upper_wick(bar) / rng >= 0.55 and _lower_wick(bar) / rng <= 0.15:
        return "shooting_star"

    if len(bars) >= 3:
        first, middle, last = bars[-3], bars[-2], bars[-1]
        if (
            first.c < first.o
            and _body(middle) / _range(middle) <= 0.35
            and last.c > last.o
            and last.c > (first.o + first.c) / 2
        ):
            return "morning_star"

    return "none"
