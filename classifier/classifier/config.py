from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8080
    model_path: str = ""
    manifest_path: str = ""
    confidence_threshold: float = 0.65
    inference_mode: Literal["auto", "onnx", "rules"] = "auto"

    @property
    def resolved_model_path(self) -> Path | None:
        if self.model_path:
            path = Path(self.model_path)
            return path if path.is_file() else None
        default = Path(__file__).resolve().parent.parent / "models" / "patterns.onnx"
        return default if default.is_file() else None

    @property
    def resolved_manifest_path(self) -> Path:
        if self.manifest_path:
            return Path(self.manifest_path)
        return Path(__file__).resolve().parent.parent / "models" / "manifest.json"


settings = Settings()

PATTERN_DIRECTIONS: dict[str, Literal["bullish", "bearish", "neutral"]] = {
    "hammer": "bullish",
    "doji": "neutral",
    "bullish_engulfing": "bullish",
    "bearish_engulfing": "bearish",
    "shooting_star": "bearish",
    "morning_star": "bullish",
}

DEFAULT_CLASSES = list(PATTERN_DIRECTIONS.keys())
