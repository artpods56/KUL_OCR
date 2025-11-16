from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from msgspec import Struct
from sqlalchemy.ext.hybrid import hybrid_property


# --- Value Objects ---


class BaseOCRValue[BaseT](Struct, tag=True):
    content: BaseT


class SimpleOCRValue(BaseOCRValue[str]):
    content: str


class SinglePageOcrValue(BaseOCRValue[str]):
    page_number: int
    content: str


class MultiPageOcrValue(BaseOCRValue[Sequence[SinglePageOcrValue]]):
    content: Sequence[SinglePageOcrValue]


OCRValueTypes = SimpleOCRValue | SinglePageOcrValue | MultiPageOcrValue


# --- Entities ---


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OCRJob:
    id: str
    document_id: str
    created_at: datetime = field(
        default_factory=datetime.now
    )  # so it gets current time when __init__ is called and not on function definition
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: JobStatus = JobStatus.PENDING

    @hybrid_property
    def is_terminal(self) -> bool:
        return self.status in (JobStatus.FAILED, JobStatus.COMPLETED)

    @hybrid_property
    def duration(self) -> timedelta:
        if not self.is_terminal:
            raise ValueError(
                f"Cannot calculate duration for job {self.id}",
                f"job is still {self.status}",
            )
        assert self.completed_at is not None
        assert self.started_at is not None
        return self.completed_at - self.started_at

    def mark_as_processing(self):
        if self.status != JobStatus.PENDING:
            raise RuntimeError(
                f"Job {self.id} has already been processed",
                f"You can only start pending jobs, but job status is {self.status}",
            )
        else:
            self.started_at = datetime.now()
            self.status = JobStatus.PROCESSING

    def complete(self):
        if self.status != JobStatus.PROCESSING:
            raise RuntimeError(
                f"Job {self.id} is not a processed job",
                f"You can only complete processed jobs, but job status is {self.status}",
            )
        else:
            self.status = JobStatus.COMPLETED
            self.completed_at = datetime.now()

    def fail(self, error_message: str):
        if self.is_terminal:
            raise RuntimeError(
                f"Cannot fail job {self.id} - job is already in a terminal state {self.status}"
            )
        else:
            self.status = JobStatus.FAILED
            self.error_message = error_message
            self.completed_at = datetime.now()


class FileType(Enum):
    PDF = "application/pdf"
    PNG = "image/png"
    JPG = "image/jpeg"
    JPEG = "image/jpeg"
    WEBP = "image/webp"

    @property
    def extension(self) -> str:
        """Get file extension"""
        return self.name.lower()

    @property
    def is_image(self) -> bool:
        return self.value.split("/")[0] == "image"


@dataclass
class Document:
    id: str
    file_path: str
    file_type: FileType
    uploaded_at: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0

    @property
    def name(self) -> str:
        return Path(self.file_path).name

    @property
    def mime_type(self) -> str:
        return self.file_type.value

    def is_pdf(self) -> bool:
        return self.file_type == FileType.PDF

    def is_image(self) -> bool:
        return self.file_type.is_image


@dataclass
class OCRResult[ContentT: BaseOCRValue[Any]]:
    id: str
    job_id: str

    content: ContentT
    creation_time: datetime = field(default_factory=datetime.now)
