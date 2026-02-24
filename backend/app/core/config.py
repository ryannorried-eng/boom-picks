from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./boom.db"
    edge_threshold: float = 0.03
    stale_snapshot_seconds: int = 180
    consensus_min_books: int = 3
    consensus_trim_outliers: bool = True
    close_capture_window_minutes: int = 10
    stale_snapshot_max_age_seconds: int = 180
    mapping_time_tolerance_minutes: int = 15
    mapping_confidence_threshold: float = 0.9

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
