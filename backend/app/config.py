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
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    query_default_limit: int = 100
    query_max_limit: int = 1000
    query_timeout_seconds: float = 10
    query_max_result_cells: int = 100_000
    query_max_sql_length: int = 10_000
    max_question_length: int = 2_000
    analysis_max_rows: int = 200_000
    analysis_sample_rows: int = 50_000
    analysis_max_result_rows: int = 1_000
    analysis_max_result_cells: int = 100_000
    analysis_max_operations: int = 10
    analysis_max_columns: int = 50
    analysis_max_groupby_columns: int = 3
    analysis_max_metrics: int = 10
    analysis_max_sort_columns: int = 3
    analysis_timeout_seconds: float = 15
    analysis_max_top_values: int = 100
    chart_max_points: int = 5_000
    chart_max_series: int = 20
    chart_max_categories: int = 100
    chart_max_pie_slices: int = 12
    chart_max_histogram_bins: int = 100
    chart_max_title_length: int = 200
    chart_max_option_bytes: int = 1_000_000
    chart_max_result_rows: int = 5_000
    agent_max_steps: int = 8
    agent_max_context_columns: int = 100
    agent_max_sample_values: int = 3
    agent_max_quality_issues: int = 20
    agent_max_correlations: int = 20
    agent_max_context_chars: int = 30_000
    agent_max_intermediate_rows: int = 100
    agent_max_intermediate_cells: int = 5_000
    agent_max_final_findings: int = 10
    agent_timeout_seconds: float = 60
    agent_max_repairs_per_step: int = 1
    agent_max_repairs_per_run: int = 3
    agent_repair_timeout_seconds: float = 15
    agent_repair_context_chars: int = 10_000
    agent_max_observation_chars: int = 4_000
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
