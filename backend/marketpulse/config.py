from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_data_base_url: str = "https://data.alpaca.markets"
    alpaca_trading_base_url: str = "https://paper-api.alpaca.markets"
    cors_origins: str = "http://localhost:5173"
    port: int = 8000

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/marketpulse"
    database_private_url: str = ""
    sync_interval_minutes: int = 5
    backfill_start_date: str = "2016-01-01"
    priority_symbols: str = "SPY,QQQ,AAPL,MSFT,GOOGL,AMZN,NVDA"
    sync_timeframes: str = "1Hour,1Day,1Week"
    priority_intraday_timeframes: str = "5Min"
    classifier_url: str = "http://localhost:8080"

    @property
    def priority_symbol_list(self) -> list[str]:
        return [s.strip().upper() for s in self.priority_symbols.split(",") if s.strip()]

    @property
    def timeframe_list(self) -> list[str]:
        return [t.strip() for t in self.sync_timeframes.split(",") if t.strip()]

    @property
    def priority_intraday_timeframe_list(self) -> list[str]:
        return [t.strip() for t in self.priority_intraday_timeframes.split(",") if t.strip()]

    @property
    def resolved_database_url(self) -> str:
        return self.database_private_url or self.database_url


settings = Settings()
