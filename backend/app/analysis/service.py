from sqlalchemy.orm import Session

from app.analysis.errors import (
    AnalysisDatasetTooLargeError,
    AnalysisError,
    AnalysisNotFoundError,
    AnalysisTimeoutError,
    AnalysisValidationError,
)
from app.analysis.process import AnalysisProcessRunner
from app.analysis.schemas import AnalysisPlan, AnalysisResponse, AnalysisRunRead
from app.config import Settings
from app.exceptions import DatasetNotFoundError
from app.models import AnalysisRun, AnalysisRunStatus
from app.repositories import AnalysisRunRepository, DatasetRepository

SAMPLE_SAFE = {"descriptive_statistics", "correlation"}


class StructuredAnalysisService:
    def __init__(
        self, session: Session, settings: Settings, runner: AnalysisProcessRunner | None = None, owner_user_id: str | None = None
    ) -> None:
        self.session = session
        self.settings = settings
        self.datasets = DatasetRepository(session, owner_user_id)
        self.runs = AnalysisRunRepository(session)
        self.runner = runner or AnalysisProcessRunner(settings)

    def execute(self, dataset_id: str, plan: AnalysisPlan) -> AnalysisResponse:
        dataset = self.datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError("Dataset 不存在")
        if len(plan.operations) > self.settings.analysis_max_operations:
            raise AnalysisValidationError("Analysis operation limit exceeded.")
        sampled = dataset.row_count > self.settings.analysis_max_rows
        if sampled and any(op.type not in SAMPLE_SAFE for op in plan.operations):
            raise AnalysisDatasetTooLargeError("This analysis requires full data and the Dataset exceeds ANALYSIS_MAX_ROWS.")
        if sampled and dataset.file_type == "xlsx":
            raise AnalysisDatasetTooLargeError("Oversized XLSX analysis is rejected to avoid loading the workbook before sampling.")
        record = self.runs.create(dataset_id, plan.model_dump(mode="json"), len(plan.operations))
        self.session.commit()
        try:
            record.status = AnalysisRunStatus.VALIDATING
            self.session.commit()
            upload_dir = self.settings.resolved_upload_dir
            path = (upload_dir / dataset.stored_filename).resolve()
            if path.parent != upload_dir or not path.is_file():
                raise AnalysisError("Managed Dataset file is unavailable.")
            record.status = AnalysisRunStatus.RUNNING
            self.session.commit()
            settings_payload = {
                name: getattr(self.settings, name)
                for name in (
                    "analysis_max_rows",
                    "analysis_sample_rows",
                    "analysis_max_result_rows",
                    "analysis_max_result_cells",
                    "analysis_max_operations",
                    "analysis_max_columns",
                    "analysis_max_groupby_columns",
                    "analysis_max_metrics",
                    "analysis_max_sort_columns",
                    "analysis_timeout_seconds",
                    "analysis_max_top_values",
                )
            }
            result = self.runner.run(
                {
                    "path": str(path),
                    "file_type": dataset.file_type,
                    "plan": plan.model_dump(mode="json"),
                    "sampled": sampled,
                    "source_rows": dataset.row_count,
                    "settings": settings_payload,
                }
            )
            record.status = AnalysisRunStatus.SUCCEEDED
            record.input_row_count = dataset.row_count
            record.output_row_count = result.row_count
            record.execution_time_ms = result.execution_time_ms
            record.result_summary_json = {
                "columns": result.columns,
                "row_count": result.row_count,
                "truncated": result.truncated,
                "operations_executed": [trace.model_dump() for trace in result.operations_executed],
                "warnings": result.warnings,
                "metadata": result.metadata,
            }
            self.session.commit()
            self.session.refresh(record)
            return AnalysisResponse(analysis=run_read(record), result=result)
        except (AnalysisError, AnalysisTimeoutError) as exc:
            self.session.rollback()
            failed = self.runs.get(dataset_id, record.id)
            if failed:
                failed.status = AnalysisRunStatus.TIMED_OUT if isinstance(exc, AnalysisTimeoutError) else AnalysisRunStatus.FAILED
                failed.error_code = exc.code
                failed.error_message = exc.detail
                self.session.commit()
            raise

    def list(self, dataset_id, page, page_size):
        if self.datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFoundError("Dataset 不存在")
        return self.runs.list(dataset_id, page, page_size)

    def get(self, dataset_id, run_id):
        if self.datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFoundError("Dataset 不存在")
        record = self.runs.get(dataset_id, run_id)
        if record is None:
            raise AnalysisNotFoundError("Analysis Run 不存在")
        return record


def run_read(record: AnalysisRun) -> AnalysisRunRead:
    return AnalysisRunRead(
        id=record.id,
        dataset_id=record.dataset_id,
        status=record.status,
        request_json=record.request_json,
        result_summary_json=record.result_summary_json,
        operation_count=record.operation_count,
        input_row_count=record.input_row_count,
        output_row_count=record.output_row_count,
        execution_time_ms=record.execution_time_ms,
        error_code=record.error_code,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
