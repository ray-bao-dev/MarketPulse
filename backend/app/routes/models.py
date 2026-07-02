import asyncio

from fastapi import APIRouter

from marketpulse.config import settings
from marketpulse.services.model_store import fetch_active_model

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/status")
async def models_status() -> dict:
    record = await asyncio.to_thread(fetch_active_model, settings.resolved_database_url)
    if not record:
        return {"active": None}
    return {
        "active": {
            "id": record["id"],
            "version": record["version"],
            "created_at": record["created_at"],
            "onnx_bytes": len(record["onnx_data"]),
            "manifest": record["manifest"],
        }
    }
