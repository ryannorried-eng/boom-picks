from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./boom.db"
    edge_threshold: float = 0.03
    stale_snapshot_seconds: int = 180
    mapping_confidence_threshold: float = 0.9

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
