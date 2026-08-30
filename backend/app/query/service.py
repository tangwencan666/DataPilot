import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import DatasetNotFoundError, QueryError, QueryExecutionError, QueryNotFoundError
from app.models import AnalysisQuery, QueryStatus
from app.query.context import DatasetSchemaContextBuilder
from app.query.executor import DuckDBQueryExecutor
from app.query.provider import LLMProvider
from app.query.schemas import QueryResponse
from app.query.validator import SQLValidator
from app.repositories import AnalysisQueryRepository, DatasetProfileRepository, DatasetRepository

logger = logging.getLogger(__name__)


class NaturalLanguageSQLService:
    def __init__(self, session: Session, settings: Settings, provider: LLMProvider) -> None:
        self.session = session; self.settings = settings; self.provider = provider
        self.datasets = DatasetRepository(session); self.profiles = DatasetProfileRepository(session); self.queries = AnalysisQueryRepository(session)

    def run(self, dataset_id: str, question: str) -> QueryResponse:
        dataset = self.datasets.get_by_id(dataset_id)
        if dataset is None: raise DatasetNotFoundError("Dataset 不存在")
        question = question.strip()
        if not question or len(question) > self.settings.max_question_length:
            error = QueryError("Question is empty or exceeds the configured length limit."); error.code = "INVALID_QUESTION"; raise error
        record = self.queries.create(dataset_id, question); self.session.commit(); logger.info("query=%s dataset=%s status=PENDING", record.id, dataset_id)
        try:
            self._status(record, QueryStatus.GENERATING)
            context = DatasetSchemaContextBuilder().build(dataset, self.profiles.get_by_dataset_id(dataset_id))
            generation = self.provider.generate_sql(question, context)
            self._status(record, QueryStatus.VALIDATING)
            validated = SQLValidator(self.settings).validate(generation.sql)
            logger.info("query=%s dataset=%s sql_validation=passed", record.id, dataset_id)
            record.generated_sql = validated.sql; record.explanation = generation.explanation
            self._status(record, QueryStatus.EXECUTING)
            upload_dir = self.settings.resolved_upload_dir; path = (upload_dir / dataset.stored_filename).resolve()
            if path.parent != upload_dir or not path.is_file(): raise QueryExecutionError("Managed dataset file is unavailable.")
            result = DuckDBQueryExecutor(self.settings).execute(path, dataset.file_type, validated)
            record.status = QueryStatus.SUCCEEDED; record.row_count = result.row_count; record.execution_time_ms = result.execution_time_ms
            self.session.commit(); self.session.refresh(record); logger.info("query=%s dataset=%s status=SUCCEEDED duration_ms=%s", record.id, dataset_id, result.execution_time_ms)
            return QueryResponse(query=query_read(record), generation=generation.model_copy(update={"sql": validated.sql}), result=result)
        except QueryError as exc:
            self.session.rollback(); failed = self.queries.get(dataset_id, record.id)
            if failed:
                failed.status = QueryStatus.FAILED; failed.error_code = exc.code; failed.error_message = exc.detail
                self.session.commit()
            logger.warning("query=%s dataset=%s status=FAILED code=%s", record.id, dataset_id, exc.code)
            raise
        except Exception as exc:
            self.session.rollback(); failed = self.queries.get(dataset_id, record.id)
            if failed:
                failed.status = QueryStatus.FAILED; failed.error_code = "QUERY_EXECUTION_FAILED"; failed.error_message = "Natural language query failed."
                self.session.commit()
            raise QueryExecutionError("Natural language query failed.") from exc

    def list(self, dataset_id: str, page: int, page_size: int):
        if self.datasets.get_by_id(dataset_id) is None: raise DatasetNotFoundError("Dataset 不存在")
        return self.queries.list(dataset_id, page, page_size)

    def get(self, dataset_id: str, query_id: str) -> AnalysisQuery:
        if self.datasets.get_by_id(dataset_id) is None: raise DatasetNotFoundError("Dataset 不存在")
        record = self.queries.get(dataset_id, query_id)
        if record is None: raise QueryNotFoundError("Analysis Query 不存在")
        return record

    def _status(self, record: AnalysisQuery, status: QueryStatus) -> None:
        record.status = status; self.session.commit(); logger.info("query=%s dataset=%s status=%s", record.id, record.dataset_id, status.value)


def query_read(record: AnalysisQuery):
    from app.query.schemas import AnalysisQueryRead
    return AnalysisQueryRead(id=record.id, dataset_id=record.dataset_id, question=record.question, generated_sql=record.generated_sql,
        explanation=record.explanation, status=record.status, row_count=record.row_count, execution_time_ms=record.execution_time_ms,
        error_code=record.error_code, error_message=record.error_message, created_at=record.created_at, updated_at=record.updated_at)
