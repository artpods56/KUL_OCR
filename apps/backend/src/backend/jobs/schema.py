from datetime import datetime
from typing import Self, ClassVar
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from core.domain import enums, model

from . import dto


class CreateJobRequest(BaseModel):
    """Request to create a new OCR job."""

    document_id: UUID = Field(..., description="ID of the document to process")


class JobResponse(BaseModel):
    """Schema for OCR job status and metadata."""

    id: UUID
    document_id: UUID
    status: enums.JobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    @classmethod
    def from_domain(cls, job: model.Job) -> Self:
        return cls(
            id=UUID(job.id),
            document_id=UUID(job.document_id),
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

    @classmethod
    def from_dto(cls, job: dto.JobDTO) -> Self:
        """Convert JobDTO to JobResponse schema."""
        return cls(
            id=UUID(job.id),
            document_id=UUID(job.document_id),
            status=enums.JobStatus(job.status),  # String back to enum
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )


class JobListResponse(BaseModel):
    """Paginated list of OCR jobs."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=False)

    jobs: list[JobResponse]
    total: int
    skip: int
    limit: int

    @classmethod
    def from_domain(cls, jobs: list[model.Job]) -> Self:
        return cls(
            jobs=[JobResponse.from_domain(job) for job in jobs],
            total=len(jobs),
            skip=0,
            limit=len(jobs),
        )
