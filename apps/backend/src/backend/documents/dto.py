from dataclasses import dataclass
from datetime import datetime
from typing import Self, Sequence

from core.domain import model


@dataclass(frozen=True)
class DocumentDTO:
    id: str
    original_filename: str
    file_type: str
    uploaded_at: datetime
    file_size_bytes: int
    file_path: str | None = None

    @classmethod
    def from_domain(cls, document: model.Document) -> Self:
        return cls(
            id=document.id,
            original_filename=document.original_filename or "unknown",
            file_type=document.file_type.value,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
            file_path=document.file_path,
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
