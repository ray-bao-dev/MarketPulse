"""Store and load ONNX model artifacts in PostgreSQL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from marketpulse.db.models import ModelArtifact
from marketpulse.db.sync_url import sync_database_url


def _session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(sync_database_url(database_url), pool_pre_ping=True)
    return sessionmaker(bind=engine)


def save_active_model(
    database_url: str,
    *,
    version: str,
    onnx_bytes: bytes,
    manifest: dict[str, Any],
    training_meta: dict[str, Any] | None = None,
) -> int:
    """Persist a new model version and mark it as the only active artifact."""
    factory = _session_factory(database_url)
    with factory() as session:
        session.execute(update(ModelArtifact).where(ModelArtifact.is_active.is_(True)).values(is_active=False))
        artifact = ModelArtifact(
            version=version,
            onnx_data=onnx_bytes,
            manifest=manifest,
            training_meta=training_meta,
            is_active=True,
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        return artifact.id


def fetch_active_model(database_url: str) -> dict[str, Any] | None:
    factory = _session_factory(database_url)
    with factory() as session:
        artifact = session.scalar(
            select(ModelArtifact)
            .where(ModelArtifact.is_active.is_(True))
            .order_by(ModelArtifact.created_at.desc())
            .limit(1)
        )

    if artifact is None:
        return None

    return {
        "id": artifact.id,
        "version": artifact.version,
        "onnx_data": bytes(artifact.onnx_data),
        "manifest": dict(artifact.manifest),
        "training_meta": dict(artifact.training_meta) if artifact.training_meta else None,
        "created_at": artifact.created_at.isoformat(),
    }


def load_active_model_to_dir(database_url: str, model_dir: Path) -> dict[str, Any] | None:
    """Write the active DB model to model_dir/patterns.onnx and manifest.json."""
    record = fetch_active_model(database_url)
    if not record:
        return None

    model_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = model_dir / "patterns.onnx"
    manifest_path = model_dir / "manifest.json"

    onnx_path.write_bytes(record["onnx_data"])
    manifest_path.write_text(json.dumps(record["manifest"], indent=2), encoding="utf-8")

    return {
        "source": "database",
        "version": record["version"],
        "artifact_id": record["id"],
        "onnx_source": str(onnx_path),
        "manifest_source": str(manifest_path),
        "onnx_present": True,
        "manifest_present": True,
        "onnx_bytes": len(record["onnx_data"]),
        "created_at": record["created_at"],
    }
