from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID
from collections.abc import Sequence
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo

from kul_ocr.domain import model, structs, enums
from kul_ocr.utils.misc import nobeartype
from kul_ocr.domain.enums import JobStatus


class DocumentResponse(BaseModel):
    """Schema for document basic information with strict validation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=True)

    ALLOWED_MIME_TYPES: ClassVar[set[str]] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    }

    id: UUID = Field(..., description="Unique UUID of the document")
    original_filename: str = Field(..., description="Original filename as uploaded by the client")
    file_type: enums.FileType = Field(..., description="MIME type of the file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    file_size_bytes: int = Field(
        ..., ge=0, description="Size of the file in bytes (must be non-negative)"
    )
    file_path: str | None = Field(
        None, min_length=1, max_length=500, description="Path to the stored file"
    )

    @field_validator("original_filename")
    @classmethod
    def validate_original_filename(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Original filename cannot be empty or whitespace only")
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError(
                "Original filename cannot contain path traversal characters"
            )
        if len(v) > 500:
            raise ValueError(
                "Original filename exceeds maximum length of 500 characters"
            )
        return v

    @field_validator("file_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unsupported file type: {v}. Allowed: {', '.join(cls.ALLOWED_MIME_TYPES)}"
            )
        return v

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if ".." in v:
                raise ValueError("File path cannot contain traversal characters (..)")
        return v

    @classmethod
    def from_domain(cls, document: model.Document) -> Self:
        return cls(
            id=UUID(document.id),
            original_filename=document.original_filename,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
            file_path=document.file_path,
        )

    @classmethod
    def from_dto(cls, document: structs.DocumentDTO) -> Self:
        return cls(
            id=UUID(document.id),
            original_filename=document.original_filename,
            file_type=enums.FileType(document.file_type),
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
            file_path=document.file_path,
        )


class DocumentListResponse(BaseModel):
    """List of documents."""

    documents: list[DocumentResponse]
    total: int

    @classmethod
    def from_domain(cls, documents: list[model.Document]) -> Self:
        return cls(
            documents=[DocumentResponse.from_domain(doc) for doc in documents],
            total=len(documents),
        )

    @classmethod
    def from_dto(cls, documents: Sequence[structs.DocumentDTO]) -> Self:
        return cls(
            documents=[DocumentResponse.from_dto(doc) for doc in documents],
            total=len(documents),
        )


class TextPartResponse(BaseModel):
    text: str
    confidence: float | None = None
    level: str

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class PagePartResponse(BaseModel):
    page_number: int
    width: int
    height: int
    parts: list[TextPartResponse]

    @field_validator("page_number")
    @classmethod
    def validate_page_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page number must be at least 1")
        return v

    @field_validator("width", "height")
    @classmethod
    @nobeartype
    def validate_dimensions(cls, v: int, info: ValidationInfo) -> int:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive (got {v})")
        return v


class ResultContentResponse(BaseModel):
    pages: list[PagePartResponse]

    @field_validator("pages")
    @classmethod
    def validate_pages_not_empty(
        cls, v: list[PagePartResponse]
    ) -> list[PagePartResponse]:
        if not v:
            raise ValueError("Result must contain at least one page")
        return v

    @classmethod
    def from_result_content(cls, content: Sequence[model.ProcessedPage]) -> Self:
        """Convert ProcessedPage sequence to ResultContentResponse.

        Used by both from_domain() and from_dto() to avoid duplication.
        """
        pages = []
        for processed_page in content:
            parts = [
                TextPartResponse(
                    text=part.text,
                    confidence=part.confidence,
                    level=part.level,
                )
                for part in processed_page.result.parts
            ]
            page_response = PagePartResponse(
                page_number=processed_page.result.metadata.page_number,
                width=processed_page.result.metadata.width,
                height=processed_page.result.metadata.height,
                parts=parts,
            )
            pages.append(page_response)
        return cls(pages=pages)

    @classmethod
    def from_domain(cls, result: model.Result) -> Self:
        return cls.from_result_content(result.content)


class ResultResponse(BaseModel):
    """Schema for OCR result."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=False)

    id: UUID = Field(..., description="Result UUID")
    job_id: UUID = Field(..., description="Associated Job UUID")
    content: ResultContentResponse = Field(..., description="Extracted OCR content")
    creation_time: datetime

    @classmethod
    def from_domain(cls, result: model.Result) -> Self:
        return cls(
            id=UUID(result.id),
            job_id=UUID(result.job_id),
            content=ResultContentResponse.from_domain(result),
            creation_time=result.creation_time,
        )

    @classmethod
    def from_dto(cls, result: structs.ResultDTO) -> Self:
        """Convert ResultDTO to ResultResponse schema."""
        return cls(
            id=UUID(result.id),
            job_id=UUID(result.job_id),
            content=ResultContentResponse.from_result_content(result.content),
            creation_time=result.creation_time,
        )


class DocumentWithResultResponse(BaseModel):
    """Document with its latest OCR result using composition."""

    document: DocumentResponse
    latest_result: ResultResponse | None = None

    @classmethod
    def from_domain(
        cls,
        document: model.Document,
        result: model.Result | None = None,
    ) -> Self:
        return cls(
            document=DocumentResponse.from_domain(document),
            latest_result=ResultResponse.from_domain(result) if result else None,
        )


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
    def from_dto(cls, job: structs.JobDTO) -> Self:
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


class TaskResponse(BaseModel):
    id: UUID = Field(..., description="UUID of the task")


class ProcessJobTaskResponse(TaskResponse):
    job_id: UUID
    task_id: UUID
    status: JobStatus


class OutboxEntryResponse(BaseModel):
    id: UUID
    event_type: enums.OutboxEventType
    aggregate_id: UUID
    created_at: datetime
    is_pending: bool
    relayed_at: datetime | None

    @classmethod
    def from_dto(cls, entry: structs.OutboxEntryDTO) -> Self:
        return cls(
            id=UUID(entry.id),
            aggregate_id=UUID(entry.aggregate_id),
            event_type=enums.OutboxEventType(entry.event_type),
            created_at=entry.created_at,
            is_pending=entry.is_pending,
            relayed_at=entry.relayed_at,
        )


class OutboxRelayerResponse(BaseModel):
    relayed_entries: list[OutboxEntryResponse]
    total: int

    @classmethod
    def from_dto(cls, entries: Sequence[structs.OutboxEntryDTO]) -> Self:
        return cls(
            relayed_entries=[OutboxEntryResponse.from_dto(entry) for entry in entries],
            total=len(entries),
        )
