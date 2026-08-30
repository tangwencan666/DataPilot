import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.charts.errors import ChartError, ChartNotFoundError, OptionTooLargeError
from app.charts.schemas import ChartDataSummary, ChartRead, ChartResult, ChartSpec
from app.charts.transformer import prepare_chart
from app.config import Settings
from app.exceptions import DatasetNotFoundError
from app.models import Chart, ChartStatus
from app.parsers import load_dataframe
from app.repositories import ChartRepository, DatasetRepository


class ChartService:
    def __init__(self, session: Session, settings: Settings, owner_user_id: str | None = None) -> None:
        self.session = session
        self.settings = settings
        self.datasets = DatasetRepository(session, owner_user_id)
        self.charts = ChartRepository(session)

    def create(self, dataset_id: str, spec: ChartSpec) -> ChartResult:
        dataset = self.datasets.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError("Dataset 不存在")
        record = self.charts.create(dataset_id, spec.model_dump(mode="json"))
        self.session.commit()
        try:
            record.status = ChartStatus.GENERATING
            self.session.commit()
            root = self.settings.resolved_upload_dir
            path = (root / dataset.stored_filename).resolve()
            if path.parent != root or not path.is_file():
                raise ChartError("Managed Dataset file is unavailable.")
            frame, _ = load_dataframe(path.read_bytes(), dataset.file_type)
            prepared = prepare_chart(frame, spec, self.settings)
            payload = json.dumps(prepared.option, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
            if len(payload) > self.settings.chart_max_option_bytes:
                raise OptionTooLargeError("Generated option exceeds CHART_MAX_OPTION_BYTES.")
            record.option_json = prepared.option
            record.status = ChartStatus.READY
            record.source_row_count = prepared.source_count
            record.rendered_point_count = prepared.rendered_count
            record.sampled = prepared.sampled
            self.session.commit()
            self.session.refresh(record)
            return ChartResult(
                chart_id=record.id,
                type=record.chart_type,
                title=record.title,
                spec=record.spec_json,
                echarts_option=record.option_json,
                data_summary=ChartDataSummary(
                    source_row_count=record.source_row_count,
                    rendered_point_count=record.rendered_point_count,
                    sampled=record.sampled,
                    warnings=prepared.warnings,
                ),
                source_row_count=record.source_row_count,
                rendered_point_count=record.rendered_point_count,
                sampled=record.sampled,
                warnings=prepared.warnings,
                generated_at=record.updated_at,
            )
        except ChartError as exc:
            self.session.rollback()
            failed = self.charts.get(dataset_id, record.id)
            if failed:
                failed.status = ChartStatus.FAILED
                failed.error_code = exc.code
                failed.error_message = exc.detail
                self.session.commit()
            raise
        except Exception as exc:
            self.session.rollback()
            failed = self.charts.get(dataset_id, record.id)
            if failed:
                failed.status = ChartStatus.FAILED
                failed.error_code = "CHART_GENERATION_FAILED"
                failed.error_message = "Chart generation failed."
                self.session.commit()
            raise ChartError("Chart generation failed.") from exc

    def list(self, dataset_id: str, page: int, page_size: int):
        if self.datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFoundError("Dataset 不存在")
        return self.charts.list(dataset_id, page, page_size)

    def get(self, dataset_id: str, chart_id: str) -> Chart:
        if self.datasets.get_by_id(dataset_id) is None:
            raise DatasetNotFoundError("Dataset 不存在")
        chart = self.charts.get(dataset_id, chart_id)
        if chart is None:
            raise ChartNotFoundError("Chart 不存在")
        return chart

    def delete(self, dataset_id: str, chart_id: str) -> None:
        chart = self.get(dataset_id, chart_id)
        self.charts.delete(chart)
        self.session.commit()


def chart_read(chart: Chart) -> ChartRead:
    return ChartRead.model_validate(chart)
