from datetime import datetime
from typing import ClassVar, Self, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.documents import dto
from backend.schemas import ResultContentResponse
from core.domain import enums, model


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
    original_filename: str = Field(
        ..., description="Original filename as uploaded by the client"
    )
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
            original_filename=document.original_filename or "unknown",
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
            file_path=document.file_path,
        )

    @classmethod
    def from_dto(cls, document: dto.DocumentDTO) -> Self:
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
    def from_dto(cls, documents: Sequence[dto.DocumentDTO]) -> Self:
        return cls(
            documents=[DocumentResponse.from_dto(doc) for doc in documents],
            total=len(documents),
        )


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
    def from_dto(cls, result: dto.ResultDTO) -> Self:
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
