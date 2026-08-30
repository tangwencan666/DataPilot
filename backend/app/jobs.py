"""Queue-neutral contracts for moving long-running services off-request later."""

import enum
from dataclasses import dataclass
from typing import Protocol


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class JobRef:
    id: str
    status: JobStatus


class JobBackend(Protocol):
    """Minimal boundary suitable for an in-process, ARQ, or Celery adapter."""

    def enqueue(self, kind: str, payload: dict[str, object]) -> JobRef: ...

    def status(self, job_id: str) -> JobRef: ...
