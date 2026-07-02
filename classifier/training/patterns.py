"""MVP pattern classes and TA-Lib CDL function mappings."""

from __future__ import annotations

# Index 0 is the implicit negative / no-pattern class for the CNN.
MVP_CLASSES: list[str] = [
    "none",
    "hammer",
    "doji",
    "bullish_engulfing",
    "bearish_engulfing",
    "shooting_star",
    "morning_star",
]

CLASS_TO_IDX: dict[str, int] = {name: idx for idx, name in enumerate(MVP_CLASSES)}

# TA-Lib function name -> canonical label (engulfing handled separately by sign).
TALIB_SINGLE_PATTERNS: dict[str, str] = {
    "CDLHAMMER": "hammer",
    "CDLDOJI": "doji",
    "CDLSHOOTINGSTAR": "shooting_star",
    "CDLMORNINGSTAR": "morning_star",
}

MIN_SIGNAL_STRENGTH = 100
