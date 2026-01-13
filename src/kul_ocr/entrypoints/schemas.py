from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kul_ocr.domain import model
from kul_ocr.domain.model import JobStatus


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
    file_path: str = Field(
        ..., min_length=1, max_length=500, description="Path to the stored file"
    )
    file_type: str = Field(..., description="MIME type of the file")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    file_size_bytes: int = Field(
        ..., ge=0, description="Size of the file in bytes (must be non-negative)"
    )

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("File path cannot be empty or whitespace only")
        if ".." in v:
            raise ValueError("File path cannot contain traversal characters (..)")
        return v

    @field_validator("file_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unsupported file type: {v}. Allowed: {', '.join(cls.ALLOWED_MIME_TYPES)}"
            )
        return v

    @classmethod
    def from_domain(cls, document: model.Document) -> Self:
        return cls(
            id=UUID(document.id),
            file_path=document.file_path,
            file_type=(
                str(document.file_type.value)
                if hasattr(document.file_type, "value")
                else str(document.file_type)
            ),
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
        )


class OCRTextPartResponse(BaseModel):
    text: str
    confidence: float | None = None
    level: str


class OCRPagePartResponse(BaseModel):
    page_number: int
    width: int
    height: int
    parts: list[OCRTextPartResponse]


class OCRResultContentResponse(BaseModel):
    pages: list[OCRPagePartResponse]

    @classmethod
    def from_domain(cls, result: model.Result) -> Self:
        pages = []
        for processed_page in result.content:
            parts = [
                OCRTextPartResponse(
                    text=part.text,
                    confidence=part.confidence,
                    level=part.level,
                )
                for part in processed_page.result.parts
            ]
            page_response = OCRPagePartResponse(
                page_number=processed_page.result.metadata.page_number,
                width=processed_page.result.metadata.width,
                height=processed_page.result.metadata.height,
                parts=parts,
            )
            pages.append(page_response)
        return cls(pages=pages)


class OcrResultResponse(BaseModel):
    """Schema for OCR result."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=False)

    id: UUID = Field(..., description="Result UUID")
    job_id: UUID = Field(..., description="Associated Job UUID")
    content: OCRResultContentResponse = Field(..., description="Extracted OCR content")
    creation_time: datetime

    @classmethod
    def from_domain(cls, result: model.Result) -> Self:
        return cls(
            id=UUID(result.id),
            job_id=UUID(result.job_id),
            content=OCRResultContentResponse.from_domain(result),
            creation_time=result.creation_time,
        )


class DocumentWithResultResponse(BaseModel):
    """Document with its latest OCR result using composition."""

    document: DocumentResponse
    latest_result: OcrResultResponse | None = None

    @classmethod
    def from_domain(
        cls,
        document: model.Document,
        result: model.Result | None = None,
    ) -> Self:
        return cls(
            document=DocumentResponse.from_domain(document),
            latest_result=OcrResultResponse.from_domain(result) if result else None,
        )


class CreateOCRJobRequest(BaseModel):
    """Request to create a new OCR job."""

    document_id: UUID = Field(..., description="ID of the document to process")


class OCRJobResponse(BaseModel):
    """Schema for OCR job status and metadata."""

    id: UUID
    document_id: UUID
    status: model.JobStatus
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


class OCRJobListResponse(BaseModel):
    """Paginated list of OCR jobs."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=False)

    jobs: list[OCRJobResponse]
    total: int

    @classmethod
    def from_domain(cls, jobs: list[model.Job]) -> Self:
        return cls(
            jobs=[OCRJobResponse.from_domain(job) for job in jobs], total=len(jobs)
        )


class TaskResponse(BaseModel):
    id: UUID = Field(..., description="UUID of the task")


class ProcessOCRJobTaskResponse(TaskResponse):
    job_id: UUID
    status: JobStatus
