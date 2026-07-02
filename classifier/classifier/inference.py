from __future__ import annotations

import numpy as np

from classifier.config import PATTERN_DIRECTIONS, settings
from classifier.preprocess import ModelManifest, render_candle_window
from classifier.schemas import BarIn, PatternOut


def _body(bar: BarIn) -> float:
    return abs(bar.c - bar.o)


def _range(bar: BarIn) -> float:
    return max(bar.h - bar.l, 1e-9)


def _upper_wick(bar: BarIn) -> float:
    return bar.h - max(bar.o, bar.c)


def _lower_wick(bar: BarIn) -> float:
    return min(bar.o, bar.c) - bar.l


def detect_hammer(prev: BarIn, bar: BarIn) -> tuple[str, float] | None:
    rng = _range(bar)
    body = _body(bar)
    if body / rng > 0.35:
        return None
    if _lower_wick(bar) / rng < 0.55:
        return None
    if _upper_wick(bar) / rng > 0.15:
        return None
    if bar.c < prev.c:
        return None
    return "hammer", 0.72


def detect_doji(_prev: BarIn, bar: BarIn) -> tuple[str, float] | None:
    rng = _range(bar)
    if _body(bar) / rng > 0.12:
        return None
    return "doji", 0.68


def detect_bullish_engulfing(prev: BarIn, bar: BarIn) -> tuple[str, float] | None:
    if prev.c >= prev.o:
        return None
    if bar.c <= bar.o:
        return None
    if bar.o <= prev.c and bar.c >= prev.o:
        return "bullish_engulfing", 0.75
    return None


def detect_bearish_engulfing(prev: BarIn, bar: BarIn) -> tuple[str, float] | None:
    if prev.c <= prev.o:
        return None
    if bar.c >= bar.o:
        return None
    if bar.o >= prev.c and bar.c <= prev.o:
        return "bearish_engulfing", 0.75
    return None


def detect_shooting_star(_prev: BarIn, bar: BarIn) -> tuple[str, float] | None:
    rng = _range(bar)
    body = _body(bar)
    if body / rng > 0.35:
        return None
    if _upper_wick(bar) / rng < 0.55:
        return None
    if _lower_wick(bar) / rng > 0.15:
        return None
    return "shooting_star", 0.7


def detect_morning_star(bars: list[BarIn]) -> tuple[str, float] | None:
    if len(bars) < 3:
        return None
    first, middle, last = bars[-3], bars[-2], bars[-1]
    if first.c >= first.o:
        return None
    if _body(middle) / _range(middle) > 0.35:
        return None
    if last.c <= last.o:
        return None
    if last.c <= (first.o + first.c) / 2:
        return None
    return "morning_star", 0.73


RULE_DETECTORS = [
    detect_hammer,
    detect_doji,
    detect_bullish_engulfing,
    detect_bearish_engulfing,
    detect_shooting_star,
]


class PatternEngine:
    def __init__(self) -> None:
        self.manifest = ModelManifest.load(settings.resolved_manifest_path)
        self.mode = "rules"
        self.session = None
        self.input_name: str | None = None
        self.output_name: str | None = None

        if settings.inference_mode == "rules":
            return

        model_path = settings.resolved_model_path
        if settings.inference_mode == "onnx" and model_path is None:
            raise RuntimeError("MODEL_PATH is required when INFERENCE_MODE=onnx")

        if model_path is not None:
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                str(model_path),
                providers=["CPUExecutionProvider"],
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.mode = "onnx"
            manifest_path = settings.resolved_manifest_path
            if manifest_path.is_file():
                self.manifest = ModelManifest.load(manifest_path)

    @property
    def model_version(self) -> str:
        return self.manifest.version

    def detect_rules(self, bars: list[BarIn]) -> list[PatternOut]:
        threshold = settings.confidence_threshold
        patterns: list[PatternOut] = []
        seen: set[str] = set()

        for idx in range(1, len(bars)):
            prev = bars[idx - 1]
            bar = bars[idx]
            key_base = bar.t

            for detector in RULE_DETECTORS:
                result = detector(prev, bar)
                if result is None:
                    continue
                label, confidence = result
                if confidence < threshold:
                    continue
                key = f"{key_base}:{label}"
                if key in seen:
                    continue
                seen.add(key)
                patterns.append(
                    PatternOut(
                        t=bar.t,
                        label=label,
                        confidence=confidence,
                        direction=PATTERN_DIRECTIONS.get(label, "neutral"),
                    )
                )

            morning = detect_morning_star(bars[: idx + 1])
            if morning is not None:
                label, confidence = morning
                if confidence >= threshold:
                    key = f"{key_base}:{label}"
                    if key not in seen:
                        seen.add(key)
                        patterns.append(
                            PatternOut(
                                t=bar.t,
                                label=label,
                                confidence=confidence,
                                direction=PATTERN_DIRECTIONS.get(label, "neutral"),
                            )
                        )

        return patterns

    def detect_onnx(self, bars: list[BarIn]) -> list[PatternOut]:
        if self.session is None or self.input_name is None or self.output_name is None:
            return self.detect_rules(bars)

        window = self.manifest.window_size
        threshold = max(settings.confidence_threshold, self.manifest.threshold)
        patterns: list[PatternOut] = []
        seen: set[str] = set()

        for end_idx in range(window - 1, len(bars)):
            window_bars = bars[end_idx - window + 1 : end_idx + 1]
            image = render_candle_window(
                [b.model_dump() for b in window_bars],
                image_size=self.manifest.image_size,
            )
            tensor = image[np.newaxis, :, :, :]
            logits = self.session.run([self.output_name], {self.input_name: tensor})[0]
            probs = _softmax(logits[0])
            class_idx = int(np.argmax(probs))
            confidence = float(probs[class_idx])
            if class_idx >= len(self.manifest.classes):
                continue
            label = self.manifest.classes[class_idx]
            if label == "none" or confidence < threshold:
                continue
            bar = window_bars[-1]
            key = f"{bar.t}:{label}"
            if key in seen:
                continue
            seen.add(key)
            patterns.append(
                PatternOut(
                    t=bar.t,
                    label=label,
                    confidence=round(confidence, 4),
                    direction=PATTERN_DIRECTIONS.get(label, "neutral"),
                )
            )

        return patterns

    def detect(self, bars: list[BarIn]) -> list[PatternOut]:
        if len(bars) < 2:
            return []
        if self.mode == "onnx":
            return self.detect_onnx(bars)
        return self.detect_rules(bars)


def _softmax(x: np.ndarray) -> np.ndarray:
    shifted = x - np.max(x)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


_engine: PatternEngine | None = None


def get_engine() -> PatternEngine:
    global _engine
    if _engine is None:
        _engine = PatternEngine()
    return _engine
