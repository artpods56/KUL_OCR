from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import ClassVar, Literal, TypedDict

from PIL import Image

from core.domain import exceptions
from core.domain.enums import DocumentStatus, FileType, JobStatus, OutboxEventType
from core.domain.exceptions import (
    InvalidJobStatusTransitionError,
    OutboxEntryAlreadyRelayedError,
)
from core.utils.misc import generate_id

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

type AllowedJobStatusTransitions = dict[JobStatus, tuple[tuple[JobStatus, ...], str]]


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

    _ALLOWED_TRANSITIONS: ClassVar[AllowedJobStatusTransitions] = {
        JobStatus.PENDING: (
            (JobStatus.PROCESSING, JobStatus.FAILED),
            "Pending jobs can only start processing or fail.",
        ),
        JobStatus.PROCESSING: (
            (JobStatus.COMPLETED, JobStatus.FAILED),
            "Processing jobs can only complete or fail.",
        ),
        JobStatus.COMPLETED: (
            (),
            "Completed jobs cannot transition to another status.",
        ),
        JobStatus.FAILED: (
            (),
            "Failed jobs cannot transition to another status.",
        ),
    }

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

    def assign_task_id(self, task_id: str):
        self.task_id = task_id

    def update_status(self, new_status: JobStatus, error_message: str | None = None):
        if self.status == new_status:
            return

        transitions_with_reason = self._ALLOWED_TRANSITIONS.get(self.status)

        if transitions_with_reason is None:
            raise InvalidJobStatusTransitionError(
                job_id=self.id,
                current=self.status,
                attempted=new_status,
                reason="Unknown job status has been provided.",
            )

        allowed_targets, reason = transitions_with_reason

        if new_status not in allowed_targets:
            raise InvalidJobStatusTransitionError(
                job_id=self.id,
                current=self.status,
                attempted=new_status,
                reason=reason,
            )

        match new_status:
            case JobStatus.PROCESSING:
                self.started_at = datetime.now()
            case JobStatus.COMPLETED:
                self.completed_at = datetime.now()
            case JobStatus.FAILED:
                self.completed_at = datetime.now()
                self.error_message = error_message
            case _:
                pass

        self.status = new_status


type AllowedDocumentStatusTransitions = dict[
    DocumentStatus, tuple[tuple[DocumentStatus, ...], str]
]


@dataclass
class Document:
    file_type: FileType
    uploaded_at: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0
    file_path: str | None = None
    _status: DocumentStatus = DocumentStatus.PENDING
    error_message: str | None = None
    original_filename: str | None = None
    id: str = field(default_factory=generate_id)

    _ALLOWED_TRANSITIONS: ClassVar[AllowedDocumentStatusTransitions] = {
        DocumentStatus.PENDING: (
            (DocumentStatus.UPLOADING, DocumentStatus.FAILED),
            "You can only upload or fail pending documents.",
        ),
        DocumentStatus.UPLOADING: (
            (DocumentStatus.READY, DocumentStatus.FAILED),
            "You can only fail or finish uploading a document.",
        ),
        DocumentStatus.FAILED: (
            (DocumentStatus.PENDING,),
            "You can only retry by transitioning to pending first.",
        ),
        DocumentStatus.READY: (
            (
                DocumentStatus.READY,
                DocumentStatus.FAILED,
            ),
            (
                "You can only fail ready documents. "
                "Retry by failing with a reason first."
            ),
        ),
    }

    @property
    def status(self) -> DocumentStatus:
        return self._status

    def __post_init__(self):
        if self.file_path is not None:
            path = Path(self.file_path)
            if self.file_type.dot_extension != path.suffix:
                raise ValueError(
                    f"Document extension mismatch: expected {self.file_type.dot_extension} ",
                    f"but got {path.suffix}",
                )

    @property
    def name(self) -> str:
        """Return the storage filename, or original filename if no file_path is set."""
        if self.file_path is not None:
            return Path(self.file_path).name
        return self.original_filename

    @property
    def file_extension(self) -> str:
        """Return the file extension from storage path, or inferred from file_type."""
        if self.file_path is not None:
            return Path(self.file_path).suffix
        return self.file_type.dot_extension

    @property
    def mime_type(self) -> str:
        return self.file_type.value

    @property
    def display_name(self) -> str:
        """Return the original filename for display purposes."""
        return self.original_filename

    def is_pdf(self) -> bool:
        return self.file_type == FileType.PDF

    def is_image(self) -> bool:
        return self.file_type.is_image

    def update_status(self, new_status: DocumentStatus, fail_reason: str | None = None):
        if self._status == new_status:
            return

        transitions_with_reason = self._ALLOWED_TRANSITIONS.get(self._status)

        if transitions_with_reason is None:
            raise exceptions.InvalidDocumentStatusTransitionError(
                document_id=self.id,
                current=self._status,
                attempted=new_status,
                reason="Unknown document status has been provided.",
            )

        allowed_targets, reason = transitions_with_reason

        if new_status in allowed_targets:
            if new_status == DocumentStatus.FAILED:
                self.error_message = fail_reason or reason
            else:
                self.error_message = None

            self._status = new_status
            return

        else:
            raise exceptions.InvalidDocumentStatusTransitionError(
                document_id=self.id,
                current=self._status,
                attempted=new_status,
                reason=reason,
            )


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


class JobProcessingPayload(TypedDict):
    """Payload for JOB_SCHEDULING outbox events."""

    type: Literal["job_processing"]
    job_id: str


class DocumentUploadPayload(TypedDict):
    """Payload for DOCUMENT_UPLOAD outbox events."""

    type: Literal["document_upload"]
    document_id: str
    staging_file_path: str
    uploaded_file_path: str


type OutboxPayload = JobProcessingPayload | DocumentUploadPayload

TASK_NAMES = {
    OutboxEventType.JOB_SCHEDULING: "worker.tasks.process_job",
    OutboxEventType.DOCUMENT_UPLOAD: "worker.tasks.upload_document",
}


@dataclass
class OutboxEntry:
    event_type: OutboxEventType
    aggregate_id: str
    payload: OutboxPayload
    id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=datetime.now)
    relayed_at: datetime | None = None

    @property
    def is_relayed(self) -> bool:
        return self.relayed_at is not None

    def mark_as_relayed(self) -> None:
        if self.is_relayed:
            raise OutboxEntryAlreadyRelayedError(entry_id=self.id)
        self.relayed_at = datetime.now()


@dataclass(slots=True)
class PageInput:
    image: Image.Image
    page_number: int
    original_document_id: str


@dataclass(slots=True, frozen=True)
class DocumentInput:
    id: str
    file_path: str
    file_type: FileType
