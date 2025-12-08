import uuid
from datetime import datetime
from typing import ClassVar
from pydantic import BaseModel, Field, field_validator
from kul_ocr.domain import model


class DocumentResponse(BaseModel):
    """Schema for document basic information with strict validation."""

    ALLOWED_MIME_TYPES: ClassVar[set[str]] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp"
    }

    id: str = Field(..., description="Unique UUID of the document")
    
    file_path: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        description="Path to the stored file"
    )
    
    file_type: str = Field(..., description="MIME type of the file")
    
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    
    file_size_bytes: int = Field(
        ..., 
        ge=0, 
        description="Size of the file in bytes (must be non-negative)"
    )

    # --- Validators ---

    @field_validator('id')
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid UUID format')
        return v

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('File path cannot be empty or whitespace only')
        if '..' in v:
            raise ValueError('File path cannot contain traversal characters (..)')
        return v

    @field_validator('file_type')
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_MIME_TYPES:
            raise ValueError(
                f'Unsupported file type: {v}. Allowed: {", ".join(cls.ALLOWED_MIME_TYPES)}'
            )
        return v

    @classmethod
    def from_domain(
        cls,
        document: model.Document,
    ) -> "DocumentResponse":
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=str(document.file_type.value) if hasattr(document.file_type, 'value') else str(document.file_type),
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
        )

    class Config:
        use_enum_values = True


class OcrResultResponse(BaseModel):
    id: str = Field(..., description="Result UUID")
    job_id: str = Field(..., description="Associated Job UUID")
    content: str = Field(..., description="Extracted text content")
    creation_time: datetime

    @field_validator('id', 'job_id')
    @classmethod
    def validate_uuids(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid UUID format')
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        return v

    @classmethod
    def from_domain(
        cls,
        result: model.OCRResult[model.SimpleOCRValue],
    ) -> "OcrResultResponse":
        return cls(
            id=result.id,
            job_id=result.job_id,
            content=result.content.content
            if hasattr(result.content, "content")
            else str(result.content),
            creation_time=result.creation_time,
        )


class DocumentWithResultResponses(DocumentResponse):
    """
    Inherits fields and validators from DocumentResponse.
    Adds the latest_result field.
    """
    latest_result: OcrResultResponse | None = None

    @classmethod
    def from_domain(
        cls,
        document: model.Document,
        result: model.OCRResult[model.SimpleOCRValue] | None = None,
    ) -> "DocumentWithResultResponses":
        base_doc = DocumentResponse.from_domain(document)
        
        return cls(
            id=base_doc.id,
            file_path=base_doc.file_path,
            file_type=base_doc.file_type,
            uploaded_at=base_doc.uploaded_at,
            file_size_bytes=base_doc.file_size_bytes,
            latest_result=(OcrResultResponse.from_domain(result) if result else None),
        )

    class Config:
        use_enum_values = True