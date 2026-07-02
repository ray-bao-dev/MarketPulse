from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException

from classifier.inference import get_engine, reset_engine
from classifier.model_loader import ensure_model_artifacts
from classifier.schemas import DetectRequest, DetectResponse

logger = logging.getLogger(__name__)

_artifact_info: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _artifact_info
    logging.basicConfig(level=logging.INFO)
    _artifact_info = ensure_model_artifacts()
    reset_engine()
    engine = get_engine()
    logger.info(
        "Classifier ready mode=%s version=%s artifacts=%s",
        engine.mode,
        engine.model_version,
        _artifact_info,
    )
    yield


app = FastAPI(title="MarketPulse Classifier", version="0.2.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    engine = get_engine()
    return {
        "status": "ok",
        "model_version": engine.model_version,
        "inference_mode": engine.mode,
        "artifacts": _artifact_info,
    }


@app.post("/v1/reload")
async def reload_model() -> dict:
    """Reload ONNX from database or configured URI (e.g. after training)."""
    global _artifact_info
    reset_engine()
    _artifact_info = ensure_model_artifacts()
    reset_engine()
    engine = get_engine()
    return {
        "status": "ok",
        "model_version": engine.model_version,
        "inference_mode": engine.mode,
        "artifacts": _artifact_info,
    }


@app.post("/v1/detect", response_model=DetectResponse)
async def detect(request: DetectRequest) -> DetectResponse:
    bars = sorted(request.bars, key=lambda b: b.t)
    if len(bars) != len(request.bars):
        raise HTTPException(status_code=400, detail="Bars must be sortable by timestamp")

    engine = get_engine()
    if request.timeframe not in engine.manifest.timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Timeframe {request.timeframe} not supported by model {engine.model_version}",
        )

    if len(bars) < engine.manifest.window_size:
        raise HTTPException(
            status_code=400,
            detail=f"At least {engine.manifest.window_size} bars required, got {len(bars)}",
        )

    patterns = engine.detect(bars)
    return DetectResponse(
        model_version=engine.model_version,
        inference_mode=engine.mode,
        patterns=patterns,
    )
