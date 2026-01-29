from dataclasses import dataclass
from datetime import datetime
from typing import Self

from core.domain import model


@dataclass(frozen=True)
class JobDTO:
    """DTO for Job entity - safe to use across async boundaries."""

    id: str
    task_id: str | None
    document_id: str
    status: str  # JobStatus enum converted to string
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    @classmethod
    def from_domain(cls, job: model.Job) -> Self:
        return cls(
            id=job.id,
            task_id=job.task_id,
            document_id=job.document_id,
            status=job.status.value,  # Enum to string
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
