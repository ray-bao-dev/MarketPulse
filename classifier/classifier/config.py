from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8080
    database_url: str = ""
    database_private_url: str = ""
    model_dir: str = "/app/models"
    model_path: str = ""
    manifest_path: str = ""
    model_uri: str = ""
    manifest_uri: str = ""
    confidence_threshold: float = 0.65
    inference_mode: Literal["auto", "onnx", "rules"] = "auto"

    @property
    def resolved_database_url(self) -> str:
        return self.database_private_url or self.database_url

    @property
    def model_dir_path(self) -> Path:
        return Path(self.model_dir)

    @property
    def resolved_model_path(self) -> Path | None:
        if self.model_path:
            path = Path(self.model_path)
            if path.is_file():
                return path

        downloaded = self.model_dir_path / "patterns.onnx"
        if downloaded.is_file():
            return downloaded

        bundled = Path(__file__).resolve().parent.parent / "models" / "patterns.onnx"
        return bundled if bundled.is_file() else None

    @property
    def resolved_manifest_path(self) -> Path:
        if self.manifest_path:
            path = Path(self.manifest_path)
            if path.is_file():
                return path

        downloaded = self.model_dir_path / "manifest.json"
        if downloaded.is_file():
            return downloaded

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
