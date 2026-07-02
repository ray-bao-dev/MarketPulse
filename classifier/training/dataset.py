"""Build labeled window dataset from exported Alpaca-style bar JSON."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from classifier.preprocess import render_candle_window
from training.bar_loader import Bar, load_bars_json
from training.labels import label_window
from training.patterns import CLASS_TO_IDX, MVP_CLASSES

CLASSES = MVP_CLASSES


def build_dataset(
    bars: list[Bar],
    *,
    window_size: int = 10,
    image_size: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    images: list[np.ndarray] = []
    labels: list[int] = []

    for end_idx in range(window_size - 1, len(bars)):
        window = bars[end_idx - window_size + 1 : end_idx + 1]
        label = label_window(window)
        image = render_candle_window(
            [
                {
                    "o": b.o,
                    "h": b.h,
                    "l": b.l,
                    "c": b.c,
                }
                for b in window
            ],
            image_size=image_size,
        )
        images.append(image)
        labels.append(CLASS_TO_IDX[label])

    if not images:
        raise ValueError("Not enough bars to build a dataset")

    x = np.stack(images, axis=0).astype(np.float32)
    y = np.array(labels, dtype=np.int64)
    return x, y


def load_npz_split(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    data = np.load(path, allow_pickle=True)
    classes = [str(c) for c in data["classes"].tolist()]
    return data["x"], data["y"], classes


def save_npz(path: Path, x: np.ndarray, y: np.ndarray, classes: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, x=x, y=y, classes=np.array(classes or CLASSES))
