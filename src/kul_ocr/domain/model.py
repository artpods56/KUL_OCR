from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Literal

from kul_ocr.exceptions import DomainException

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
    task_id: str | None = None
    status: JobStatus = JobStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        return self.status in (JobStatus.FAILED, JobStatus.COMPLETED)

    @property
    def is_active(self) -> bool:
        """Check if job is in an active (non-terminal) state."""
        return self.status in (JobStatus.PENDING, JobStatus.PROCESSING)

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
            raise InvalidJobStatusTransitionError(
                job_id=self.id,
                current=self.status,
                attempted=JobStatus.PROCESSING,
            )
        self.started_at = datetime.now()
        self.status = JobStatus.PROCESSING

    def complete(self):
        if self.status != JobStatus.PROCESSING:
            raise InvalidJobStatusTransitionError(
                job_id=self.id,
                current=self.status,
                attempted=JobStatus.COMPLETED,
            )
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, error_message: str):
        if self.is_terminal:
            raise InvalidJobStatusTransitionError(
                job_id=self.id,
                current=self.status,
                attempted=JobStatus.FAILED,
            )
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()

    def assign_task_id(self, task_id: str):
        self.task_id = task_id


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

    def validate_extension(self, filename: str) -> None:
        """Validate that filename extension matches this file type.

        Args:
            filename: Name of the file to validate.

        Raises:
            FileExtensionMismatchError: If extension doesn't match.
        """
        from pathlib import Path

        if not filename:
            return  # No filename to validate

        actual_extension = Path(filename).suffix.lower()
        if actual_extension and actual_extension != self.dot_extension:
            raise FileExtensionMismatchError(
                expected_extension=self.dot_extension, actual_extension=actual_extension
            )


@dataclass
class Document:
    id: str
    file_path: str
    file_type: FileType
    uploaded_at: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0
    original_filename: str | None = None

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

    @property
    def display_name(self) -> str:
        """Return the original filename if available, otherwise the storage name."""
        if self.original_filename:
            return self.original_filename
        return self.name

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


"""
--- Outbox Pattern ---
"""


class OutboxEventType(Enum):
    OCR_JOB_SCHEDULED = "ocr_job_scheduled"


TASK_NAMES = {
    OutboxEventType.OCR_JOB_SCHEDULED: "kul_ocr.entrypoints.tasks.process_ocr_job_task",
}


@dataclass
class OutboxEntry:
    id: str
    event_type: OutboxEventType
    aggregate_id: str
    payload: dict[str, str]
    created_at: datetime = field(default_factory=datetime.now)
    relayed_at: datetime | None = None

    @property
    def is_relayed(self) -> bool:
        return self.relayed_at is not None

    def mark_as_relayed(self) -> None:
        if self.is_relayed:
            raise OutboxEntryAlreadyRelayedError(entry_id=self.id)
        self.relayed_at = datetime.now()


class InvalidJobStatusTransitionError(DomainException):
    code: str = "INVALID_STATUS_TRANSITION"

    def __init__(self, job_id: str, current: JobStatus, attempted: JobStatus):
        msg = f"Job {job_id} cannot transition from {current.name} to {attempted.name}"

        super().__init__(
            message=msg,
            job_id=job_id,
            current_status=current.value,
            attempted_status=attempted.value,
        )


class UnsupportedFileTypeError(DomainException):
    code: str = "UNSUPPORTED_FILE_TYPE"

    def __init__(self, file_type: str, message: str | None = None):
        msg = message or f"Unsupported file type: {file_type}"
        super().__init__(message=msg, file_type=file_type)


class FileExtensionMismatchError(DomainException):
    code: str = "FILE_EXTENSION_MISMATCH"

    def __init__(
        self, expected_extension: str, actual_extension: str, message: str | None = None
    ):
        msg = message or (
            f"File extension mismatch: expected {expected_extension}, "
            f"got {actual_extension}"
        )
        super().__init__(
            message=msg,
            expected_extension=expected_extension,
            actual_extension=actual_extension,
        )


class InvalidJobStatusTransitionErrorDepr(DomainException):
    code: str = "INVALID_STATUS_TRANSITION"

    def __init__(
        self,
        job_id: str,
        current_status: str,
        attempted_status: str,
        message: str | None = None,
    ):
        msg = message or (
            f"Invalid status transition for job {job_id}: "
            f"{current_status} -> {attempted_status}"
        )
        super().__init__(
            message=msg,
            job_id=job_id,
            current_status=current_status,
            attempted_status=attempted_status,
        )


class UnknownJobStatusError(DomainException):
    code: str = "UNKNOWN_JOB_STATUS"

    def __init__(self, status: str, message: str | None = None):
        msg = message or f"Unknown job status {status}."
        super().__init__(message=msg, status=status)


class OutboxEntryAlreadyRelayedError(DomainException):
    code: str = "OUTBOX_ENTRY_ALREADY_RELAYED"

    def __init__(self, entry_id: str, message: str | None = None):
        msg = message or f"Outbox entry {entry_id} has already been relayed."
        super().__init__(message=msg, entry_id=entry_id)
