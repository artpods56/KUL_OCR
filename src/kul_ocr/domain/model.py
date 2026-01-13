from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Literal

from kul_ocr.domain import exceptions


"""
--- Value Objects ---
"""


@dataclass(frozen=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class TextPart:
    text: str
    bbox: BoundingBox
    confidence: float | None = None
    level: Literal["word", "line", "block"] = "block"


@dataclass(frozen=True)
class PageMetadata:
    page_number: int
    width: int
    height: int
    rotation: int = 0


@dataclass(frozen=True)
class PagePart:
    parts: Sequence[TextPart]
    metadata: PageMetadata

    @property
    def full_text(self) -> str:
        """Concatenated text from all TextParts."""
        return "".join(part.text for part in self.parts)


def wrap_text_in_page_part(
    text: str, page_number: int, width: int, height: int
) -> PagePart:
    """Create a PagePart with a single TextPart containing the full OCR text."""
    text_part = TextPart(
        text=text,
        bbox=BoundingBox(x_min=0.0, y_min=0.0, x_max=float(width), y_max=float(height)),
        confidence=None,
        level="block",
    )
    metadata = PageMetadata(page_number=page_number, width=width, height=height)
    return PagePart(parts=[text_part], metadata=metadata)


"""
--- Entities ---
"""


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    document_id: str
    created_at: datetime = field(default_factory=datetime.now)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: JobStatus = JobStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        return self.status in (JobStatus.FAILED, JobStatus.COMPLETED)

    @property
    def duration(self) -> timedelta:
        if not self.is_terminal:
            raise ValueError(
                f"Cannot calculate duration for job {self.id} - job is still {self.status}"
            )
        if self.completed_at is None or self.started_at is None:
            raise ValueError(f"Job {self.id} is terminal but missing timestamps")
        return self.completed_at - self.started_at

    def mark_as_processing(self):
        if self.status != JobStatus.PENDING:
            raise exceptions.InvalidJobStatusError(
                f"Job {self.id} has already been processed. Status is {self.status}"
            )
        self.started_at = datetime.now()
        self.status = JobStatus.PROCESSING

    def complete(self):
        if self.status != JobStatus.PROCESSING:
            raise exceptions.InvalidJobStatusError(
                f"Job {self.id} is not in processing state. Status is {self.status}"
            )
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, error_message: str):
        if self.is_terminal:
            raise exceptions.InvalidJobStatusError(
                f"Cannot fail job {self.id} - job is already terminal ({self.status})"
            )
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
        return self.name.lower()

    @property
    def dot_extension(self) -> str:
        return "." + self.extension

    @property
    def is_image(self) -> bool:
        return self.value.startswith("image/")


@dataclass
class Document:
    id: str
    file_path: str
    file_type: FileType
    uploaded_at: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0

    def __post_init__(self):
        path = Path(self.file_path)
        if self.file_type.dot_extension != path.suffix:
            raise ValueError(
                f"Document extension mismatch: expected {self.file_type.dot_extension} ",
                f"but got {path.suffix}",
            )

    @property
    def name(self) -> str:
        return Path(self.file_path).name

    @property
    def file_extension(self) -> str:
        return Path(self.file_path).suffix

    @property
    def mime_type(self) -> str:
        return self.file_type.value

    def is_pdf(self) -> bool:
        return self.file_type == FileType.PDF

    def is_image(self) -> bool:
        return self.file_type.is_image


@dataclass
class PageRef:
    document_id: str
    index: int


@dataclass
class ProcessedPage:
    ref: PageRef
    result: PagePart


@dataclass
class Result:
    id: str
    job_id: str
    content: Sequence[ProcessedPage]
    creation_time: datetime = field(default_factory=datetime.now)
