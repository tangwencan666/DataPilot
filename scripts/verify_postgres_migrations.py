"""Verify the Alembic head and required tables on the configured database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine, inspect, text
from app.config import get_settings

EXPECTED = {"users", "datasets", "dataset_profiles", "analysis_queries", "analysis_runs", "charts", "agent_runs", "agent_step_runs", "agent_step_attempts", "reports"}

def main() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        revision = connection.scalar(text("select version_num from alembic_version"))
    missing = EXPECTED - set(inspect(engine).get_table_names())
    if revision != "20260830_0009" or missing:
        raise SystemExit(f"migration verification failed: revision={revision}, missing={sorted(missing)}")
    print(f"migration verification passed: revision={revision}, tables={len(EXPECTED)}")

if __name__ == "__main__":
    main()
