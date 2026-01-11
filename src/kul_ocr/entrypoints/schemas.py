from datetime import datetime
from uuid import UUID

from typing import Sequence, Self, Any
from pydantic import BaseModel, Field

from kul_ocr.domain import model


class DocumentResponse(BaseModel):
    id: str
    file_path: str
    file_type: model.FileType
    uploaded_at: datetime
    file_size_bytes: int

    @classmethod
    def from_domain(
        cls,
        document: model.Document,
    ) -> "DocumentResponse":
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
        )

    class Config:
        use_enum_values = False


class OcrResultResponse(BaseModel):
    id: str
    job_id: str
    content: str
    creation_time: datetime

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

    class Config:
        use_enum_values = False


class DocumentWithResultResponses(BaseModel):
    id: str
    file_path: str
    file_type: model.FileType
    uploaded_at: datetime
    file_size_bytes: int
    latest_result: OcrResultResponse | None = None

    class Config:
        use_enum_values = False

    @classmethod
    def from_domain(
        cls, document: model.Document, result: model.OCRResult[Any] | None
    ) -> Self:
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
            latest_result=OcrResultResponse.from_domain(result) if result else None,
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
    def from_domain(cls, job: model.OCRJob) -> Self:
        return cls(
            id=job.id,
            document_id=job.document_id,
            status=job.status.value,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )


class OCRJobListResponse(BaseModel):
    jobs: list[OCRJobResponse]
    total: int

    @classmethod
    def from_domain(cls, jobs: Sequence[model.OCRJob]) -> Self:
        return cls(
            jobs=[OCRJobResponse.from_domain(job) for job in jobs], total=len(jobs)
        )
