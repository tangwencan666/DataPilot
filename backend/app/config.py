from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DataPilot API"
    app_env: str = "development"
    max_upload_mb: int = 20
    preview_row_limit: int = 20
    profile_max_rows: int = 100_000
    profile_sample_rows: int = 50_000
    profile_sample_values: int = 5
    profile_top_values: int = 10
    profile_max_correlation_columns: int = 20
    profile_max_correlations: int = 50
    profile_correlation_threshold: float = 0.5
    quality_high_missing_threshold: float = 0.3
    quality_high_duplicate_threshold: float = 0.1
    profile_high_cardinality_min: int = 50
    profile_high_cardinality_ratio: float = 0.8
    upload_dir: Path = Path("data/uploads")
    database_url: str = "postgresql+psycopg://datapilot:datapilot@localhost:5432/datapilot"
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def max_upload_size(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def resolved_upload_dir(self) -> Path:
        path = self.upload_dir
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path
        return path.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
