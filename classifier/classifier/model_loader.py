"""Download or load model artifacts on startup."""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from classifier.config import settings

logger = logging.getLogger(__name__)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s -> %s", url, dest)
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)
    logger.info("Saved %s (%s bytes)", dest.name, dest.stat().st_size)


def _load_from_database(model_dir: Path) -> dict | None:
    db_url = settings.resolved_database_url
    if not db_url:
        return None

    try:
        from marketpulse.services.model_store import load_active_model_to_dir

        return load_active_model_to_dir(db_url, model_dir)
    except Exception as exc:
        logger.error("Failed to load model from database: %s", exc)
        return {"source": "database", "error": str(exc)}


def ensure_model_artifacts() -> dict:
    """
    Load ONNX + manifest into MODEL_DIR.

    Priority:
    1. Active row in PostgreSQL (DATABASE_PRIVATE_URL / DATABASE_URL)
    2. MODEL_URI / MANIFEST_URI HTTP download
    3. MODEL_PATH / MANIFEST_PATH on disk
    4. Bundled models/ (rules fallback)
    """
    model_dir = settings.model_dir_path
    model_dir.mkdir(parents=True, exist_ok=True)

    onnx_dest = model_dir / "patterns.onnx"
    manifest_dest = model_dir / "manifest.json"

    info: dict = {
        "model_dir": str(model_dir),
        "database_configured": bool(settings.resolved_database_url),
        "model_uri": settings.model_uri or None,
        "manifest_uri": settings.manifest_uri or None,
        "onnx_present": False,
        "manifest_present": False,
    }

    db_info = _load_from_database(model_dir)
    if db_info and db_info.get("onnx_present"):
        info.update(db_info)
        return info
    if db_info and db_info.get("error"):
        info["database_error"] = db_info["error"]

    if settings.model_path and Path(settings.model_path).is_file():
        info["onnx_present"] = True
        info["onnx_source"] = settings.model_path
    if settings.manifest_path and Path(settings.manifest_path).is_file():
        info["manifest_present"] = True
        info["manifest_source"] = settings.manifest_path

    if settings.model_uri:
        try:
            _download(settings.model_uri, onnx_dest)
            info["onnx_present"] = True
            info["onnx_source"] = str(onnx_dest)
            info["source"] = "uri"
        except Exception as exc:
            logger.error("Failed to download MODEL_URI: %s", exc)
            info["download_error"] = str(exc)

    manifest_url = settings.manifest_uri
    if not manifest_url and settings.model_uri:
        if settings.model_uri.endswith(".onnx"):
            manifest_url = settings.model_uri[:-5] + "manifest.json"
        elif settings.model_uri.endswith("/onnx"):
            manifest_url = settings.model_uri.replace("/onnx", "/manifest")

    if manifest_url:
        try:
            _download(manifest_url, manifest_dest)
            info["manifest_present"] = True
            info["manifest_source"] = str(manifest_dest)
        except Exception as exc:
            logger.warning("Failed to download manifest (non-fatal): %s", exc)

    if onnx_dest.is_file() and not info.get("onnx_source"):
        info["onnx_present"] = True
        info["onnx_source"] = str(onnx_dest)
    if manifest_dest.is_file() and not info.get("manifest_source"):
        info["manifest_present"] = True
        info["manifest_source"] = str(manifest_dest)

    return info
