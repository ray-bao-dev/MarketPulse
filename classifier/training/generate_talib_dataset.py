"""Generate TA-Lib weak-labeled candlestick windows for CNN training."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from classifier.preprocess import render_candle_window
from training.bar_loader import Bar, load_bars_multi
from training.patterns import (
    CLASS_TO_IDX,
    MIN_SIGNAL_STRENGTH,
    MVP_CLASSES,
    TALIB_SINGLE_PATTERNS,
)


@dataclass
class Sample:
    image: np.ndarray
    label: str
    month: str
    timestamp: str
    symbol: str | None = None


def _require_talib():
    try:
        import talib  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "TA-Lib is required. Install the C library then: pip install TA-Lib"
        ) from exc
    import talib

    return talib


def patterns_at_index(
    talib,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    idx: int,
    *,
    min_strength: int = MIN_SIGNAL_STRENGTH,
) -> list[str]:
    found: list[str] = []

    for func_name, label in TALIB_SINGLE_PATTERNS.items():
        result = getattr(talib, func_name)(opens, highs, lows, closes)
        value = int(result[idx])
        if abs(value) >= min_strength:
            found.append(label)

    engulf = talib.CDLENGULFING(opens, highs, lows, closes)
    engulf_val = int(engulf[idx])
    if engulf_val >= min_strength:
        found.append("bullish_engulfing")
    elif engulf_val <= -min_strength:
        found.append("bearish_engulfing")

    return found


def label_completion_bar(
    talib,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    idx: int,
) -> str | None:
    """Return label for window ending at idx, or None if ambiguous."""
    found = patterns_at_index(talib, opens, highs, lows, closes, idx)
    if len(found) == 1:
        return found[0]
    if len(found) == 0:
        return "none"
    return None


def month_key(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m")


def build_samples(
    bars: list[Bar],
    *,
    window_size: int = 10,
    image_size: int = 64,
) -> list[Sample]:
    if len(bars) < window_size:
        raise ValueError(f"Need at least {window_size} bars, got {len(bars)}")

    talib = _require_talib()
    opens = np.array([b.o for b in bars], dtype=np.float64)
    highs = np.array([b.h for b in bars], dtype=np.float64)
    lows = np.array([b.l for b in bars], dtype=np.float64)
    closes = np.array([b.c for b in bars], dtype=np.float64)

    samples: list[Sample] = []
    for end_idx in range(window_size - 1, len(bars)):
        label = label_completion_bar(talib, opens, highs, lows, closes, end_idx)
        if label is None:
            continue

        window = bars[end_idx - window_size + 1 : end_idx + 1]
        image = render_candle_window(
            [{"o": b.o, "h": b.h, "l": b.l, "c": b.c} for b in window],
            image_size=image_size,
        )
        bar = window[-1]
        samples.append(
            Sample(
                image=image,
                label=label,
                month=month_key(bar.t),
                timestamp=bar.t,
            )
        )

    return samples


def stratified_cap(samples: list[Sample], max_per_class: int, seed: int) -> list[Sample]:
    rng = random.Random(seed)
    by_class: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        by_class[sample.label].append(sample)

    capped: list[Sample] = []
    for label, items in by_class.items():
        if len(items) <= max_per_class:
            capped.extend(items)
        else:
            capped.extend(rng.sample(items, max_per_class))
    return capped


def walk_forward_split(
    samples: list[Sample],
    *,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> dict[str, list[Sample]]:
    months = sorted({s.month for s in samples})
    if not months:
        raise ValueError("No samples to split")

    train_end = max(1, int(len(months) * train_ratio))
    val_end = max(train_end + 1, int(len(months) * (train_ratio + val_ratio)))
    train_end = min(train_end, len(months) - 2) if len(months) >= 3 else max(1, len(months) - 1)
    val_end = min(val_end, len(months) - 1) if len(months) >= 2 else len(months)

    train_months = set(months[:train_end])
    val_months = set(months[train_end:val_end])
    test_months = set(months[val_end:])

    if not test_months and val_months:
        test_months = {months[-1]}
        val_months.discard(months[-1])
    if not val_months and train_months and len(months) > 1:
        val_months = {months[train_end - 1]}
        train_months.discard(months[train_end - 1])

    return {
        "train": [s for s in samples if s.month in train_months],
        "val": [s for s in samples if s.month in val_months],
        "test": [s for s in samples if s.month in test_months],
    }


def samples_to_arrays(samples: list[Sample]) -> tuple[np.ndarray, np.ndarray]:
    if not samples:
        return np.empty((0, 1, 64, 64), dtype=np.float32), np.empty((0,), dtype=np.int64)
    x = np.stack([s.image for s in samples], axis=0).astype(np.float32)
    y = np.array([CLASS_TO_IDX[s.label] for s in samples], dtype=np.int64)
    return x, y


def save_split_npz(path: Path, samples: list[Sample]) -> dict:
    x, y = samples_to_arrays(samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, x=x, y=y, classes=np.array(MVP_CLASSES))
    counts: dict[str, int] = defaultdict(int)
    for s in samples:
        counts[s.label] += 1
    return {"path": str(path), "count": len(samples), "class_counts": dict(counts)}


def generate_dataset(
    bars: list[Bar],
    output_dir: Path,
    *,
    window_size: int = 10,
    image_size: int = 64,
    max_per_class: int = 10_000,
    seed: int = 42,
) -> dict:
    raw_samples = build_samples(bars, window_size=window_size, image_size=image_size)
    capped = stratified_cap(raw_samples, max_per_class=max_per_class, seed=seed)
    splits = walk_forward_split(capped)

    output_dir.mkdir(parents=True, exist_ok=True)
    split_meta = {}
    for name, items in splits.items():
        split_meta[name] = save_split_npz(output_dir / f"{name}.npz", items)

    manifest = {
        "version": "1.0.0",
        "window_size": window_size,
        "image_size": image_size,
        "threshold": 0.65,
        "timeframes": ["5Min"],
        "classes": MVP_CLASSES,
        "label_source": "talib",
        "filters": {
            "min_signal_strength": MIN_SIGNAL_STRENGTH,
            "single_pattern_only": True,
            "max_per_class": max_per_class,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    splits_json = {
        "seed": seed,
        "total_raw_samples": len(raw_samples),
        "total_capped_samples": len(capped),
        "splits": split_meta,
    }
    (output_dir / "splits.json").write_text(json.dumps(splits_json, indent=2), encoding="utf-8")
    return splits_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TA-Lib labeled training dataset")
    parser.add_argument("--bars", type=Path, action="append", default=[], help="JSON bar export(s)")
    parser.add_argument("--database-url", type=str, default="", help="PostgreSQL URL")
    parser.add_argument("--symbols", type=str, default="SPY,QQQ,AAPL", help="Comma-separated symbols")
    parser.add_argument("--timeframe", type=str, default="5Min")
    parser.add_argument("--start", type=str, default=None)
    parser.add_argument("--end", type=str, default=None)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--window-size", type=int, default=10)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--max-per-class", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    bars = load_bars_multi(
        database_url=args.database_url or None,
        json_paths=args.bars,
        symbols=symbols,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
    )
    if not bars:
        raise SystemExit("No bars loaded")

    meta = generate_dataset(
        bars,
        args.output,
        window_size=args.window_size,
        image_size=args.image_size,
        max_per_class=args.max_per_class,
        seed=args.seed,
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
