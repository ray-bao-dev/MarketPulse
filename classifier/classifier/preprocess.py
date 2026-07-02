from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from classifier.config import DEFAULT_CLASSES, settings


@dataclass
class ModelManifest:
    version: str
    window_size: int
    image_size: int
    classes: list[str]
    threshold: float
    timeframes: list[str]

    @classmethod
    def load(cls, path: Path) -> ModelManifest:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                version=data.get("version", "0.0.0"),
                window_size=int(data.get("window_size", 10)),
                image_size=int(data.get("image_size", 64)),
                classes=list(data.get("classes", DEFAULT_CLASSES)),
                threshold=float(data.get("threshold", settings.confidence_threshold)),
                timeframes=list(data.get("timeframes", ["5Min"])),
            )
        return cls(
            version="rules-stub",
            window_size=10,
            image_size=64,
            classes=DEFAULT_CLASSES,
            threshold=settings.confidence_threshold,
            timeframes=["5Min", "1Hour", "1Day", "1Week"],
        )


def render_candle_window(
    bars: list[dict],
    *,
    image_size: int = 64,
) -> np.ndarray:
    """Render OHLCV window to grayscale image tensor (1, H, W) float32 in [0, 1]."""
    highs = [float(b["h"]) for b in bars]
    lows = [float(b["l"]) for b in bars]
    price_min = min(lows)
    price_max = max(highs)
    span = price_max - price_min or 1.0

    img = Image.new("L", (image_size, image_size), color=0)
    draw = ImageDraw.Draw(img)
    n = len(bars)
    slot = image_size / max(n, 1)
    body_width = max(2, int(slot * 0.55))

    for idx, bar in enumerate(bars):
        o = float(bar["o"])
        h = float(bar["h"])
        l = float(bar["l"])
        c = float(bar["c"])

        x_center = int(idx * slot + slot / 2)
        y_high = int((1.0 - (h - price_min) / span) * (image_size - 1))
        y_low = int((1.0 - (l - price_min) / span) * (image_size - 1))
        y_open = int((1.0 - (o - price_min) / span) * (image_size - 1))
        y_close = int((1.0 - (c - price_min) / span) * (image_size - 1))

        draw.line([(x_center, y_high), (x_center, y_low)], fill=255, width=1)
        top = min(y_open, y_close)
        bottom = max(y_open, y_close)
        if bottom - top < 1:
            bottom = top + 1
        draw.rectangle(
            [
                x_center - body_width // 2,
                top,
                x_center + body_width // 2,
                bottom,
            ],
            fill=255,
        )

    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr[np.newaxis, :, :]
