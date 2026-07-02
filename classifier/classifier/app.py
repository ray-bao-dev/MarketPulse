from fastapi import FastAPI, HTTPException

from classifier.inference import get_engine
from classifier.schemas import DetectRequest, DetectResponse

app = FastAPI(title="MarketPulse Classifier", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    engine = get_engine()
    return {
        "status": "ok",
        "model_version": engine.model_version,
        "inference_mode": engine.mode,
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
