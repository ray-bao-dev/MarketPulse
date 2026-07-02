from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8090
    database_url: str = ""
    database_private_url: str = ""
    default_symbols: str = "SPY,QQQ,AAPL"
    default_timeframe: str = "5Min"
    default_start: str = "2025-01-01"
    artifacts_dir: str = "/app/artifacts"
    classifier_url: str = ""

    @property
    def resolved_database_url(self) -> str:
        return self.database_private_url or self.database_url

    @property
    def default_symbol_list(self) -> list[str]:
        return [s.strip().upper() for s in self.default_symbols.split(",") if s.strip()]


settings = Settings()
