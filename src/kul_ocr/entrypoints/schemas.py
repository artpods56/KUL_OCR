from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from kul_ocr.domain import model


class DocumentResponse(BaseModel):
    id: str
    file_path: str
    file_type: model.FileType
    uploaded_at: datetime
    file_size_bytes: int

    @classmethod
    def from_domain(cls, document: model.Document) -> "DocumentResponse":
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
        )


class CreateOCRJobRequest(BaseModel):
    document_id: UUID = Field(..., description="ID of the document to process")


class OCRJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    @classmethod
    def from_domain(cls, job: model.OCRJob) -> "OCRJobResponse":
        return cls(
            id=job.id,
            document_id=job.document_id,
            status=job.status.value,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

    class Config:
        use_enum_values = False
