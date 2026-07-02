from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from trainer_app.config import settings


class JobState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class JobStatus:
    state: JobState = JobState.IDLE
    step: str = ""
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "step": self.step,
            "logs": self.logs[-200:],
            "result": self.result,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


_lock = Lock()
_status = JobStatus()


def get_status() -> JobStatus:
    with _lock:
        return JobStatus(
            state=_status.state,
            step=_status.step,
            logs=list(_status.logs),
            result=dict(_status.result),
            started_at=_status.started_at,
            finished_at=_status.finished_at,
        )


def _log(message: str) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {message}"
    with _lock:
        _status.logs.append(line)


def _set_step(step: str) -> None:
    with _lock:
        _status.step = step
    _log(step)


def _run_pipeline(
    *,
    symbols: list[str],
    timeframe: str,
    start: str,
    epochs: int,
    max_per_class: int,
) -> None:
    global _status
    artifacts = Path(settings.artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)

    db_url = settings.resolved_database_url
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL or DATABASE_PRIVATE_URL is not set. "
            "Link PostgreSQL to this Railway service."
        )

    _set_step("Loading bars from PostgreSQL")
    from training.bar_loader import load_bars_multi

    bars = load_bars_multi(
        database_url=db_url,
        json_paths=[],
        symbols=symbols,
        timeframe=timeframe,
        start=start,
        end=None,
    )
    _log(f"Loaded {len(bars)} bars for {', '.join(symbols)} ({timeframe})")
    if len(bars) < 20:
        raise RuntimeError(
            f"Only {len(bars)} bars found. Ensure worker has synced {timeframe} "
            f"data for these symbols."
        )

    _set_step("Generating TA-Lib dataset")
    from training.generate_talib_dataset import generate_dataset

    meta = generate_dataset(
        bars,
        artifacts,
        max_per_class=max_per_class,
    )
    _log(f"Dataset splits: {meta.get('splits', {})}")

    _set_step("Training CNN")
    from training.train import train_from_splits

    weights = train_from_splits(artifacts, artifacts, epochs=epochs)
    _log(f"Weights saved to {weights}")

    _set_step("Exporting ONNX")
    from training.export_onnx import export_onnx

    onnx_path = artifacts / "patterns.onnx"
    manifest_path = artifacts / "manifest.json"
    export_onnx(weights, manifest_path, onnx_path)
    _log(f"ONNX exported to {onnx_path}")

    with _lock:
        _status.result = {
            "bars": len(bars),
            "symbols": symbols,
            "timeframe": timeframe,
            "onnx": str(onnx_path),
            "manifest": str(manifest_path),
            "splits": meta,
        }


def start_job(
    *,
    symbols: list[str],
    timeframe: str,
    start: str,
    epochs: int,
    max_per_class: int,
) -> bool:
    global _status
    with _lock:
        if _status.state == JobState.RUNNING:
            return False
        _status = JobStatus(
            state=JobState.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    def runner() -> None:
        global _status
        try:
            _run_pipeline(
                symbols=symbols,
                timeframe=timeframe,
                start=start,
                epochs=epochs,
                max_per_class=max_per_class,
            )
            with _lock:
                _status.state = JobState.DONE
                _status.finished_at = datetime.now(timezone.utc).isoformat()
            _log("Pipeline complete")
        except Exception as exc:
            _log(f"ERROR: {exc}")
            _log(traceback.format_exc())
            with _lock:
                _status.state = JobState.ERROR
                _status.finished_at = datetime.now(timezone.utc).isoformat()
                _status.result = {"error": str(exc)}

    Thread(target=runner, daemon=True).start()
    return True
