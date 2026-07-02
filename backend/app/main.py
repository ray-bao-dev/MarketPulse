from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from marketpulse.config import settings
from app.routes.market import router as market_router
from app.routes.analysis import router as analysis_router
from app.routes.models import router as models_router

app = FastAPI(title="MarketPulse API", version="0.2.0")

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(models_router, prefix="/api")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


def _mount_frontend() -> None:
    if not STATIC_DIR.is_dir():
        return

    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_file = STATIC_DIR / "index.html"

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        if path.startswith("api/") or path.startswith("assets/"):
            raise HTTPException(status_code=404)

        candidate = STATIC_DIR / path
        if candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(index_file)


_mount_frontend()
