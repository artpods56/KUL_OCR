from dataclasses import dataclass
from datetime import datetime
from typing import Self, Sequence

from PIL import Image

from kul_ocr.domain import model
from kul_ocr.domain.model import FileType


@dataclass(slots=True)
class PageInput:
    """Standardized input for the OCR engine."""

    image: Image.Image
    page_number: int
    original_document_id: str


@dataclass(slots=True, frozen=True)
class DocumentInput:
    """Minimal document data for OCR processing - no ORM dependencies."""

    id: str
    file_path: str
    file_type: FileType


@dataclass(frozen=True)
class DocumentDTO:
    id: str
    file_path: str
    file_type: str
    uploaded_at: datetime
    file_size_bytes: int

    @classmethod
    def from_domain(cls, document: model.Document) -> Self:
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=document.file_type.value,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
        )


@dataclass(frozen=True)
class JobDTO:
    """DTO for Job entity - safe to use across async boundaries."""

    id: str
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
            document_id=job.document_id,
            status=job.status.value,  # Enum to string
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )


@dataclass(frozen=True)
class ResultDTO:
    """DTO for Result entity - safe to use across async boundaries.

    Note: content contains ProcessedPage value objects which are already
    frozen dataclasses and don't have ORM session dependencies.
    """

    id: str
    job_id: str
    content: Sequence[model.ProcessedPage]
    creation_time: datetime

    @classmethod
    def from_domain(cls, result: model.Result) -> Self:
        return cls(
            id=result.id,
            job_id=result.job_id,
            content=result.content,  # Value objects, not entities
            creation_time=result.creation_time,
        )
