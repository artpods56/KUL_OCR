from datetime import datetime
from tarfile import data_filter

from pydantic import BaseModel

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
        result: model.Document | None,
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
    job_id:str
    content: str
    creation_time: datetime

    @classmethod
    def from_domain(
        cls,
        result: model.OCRResult,
        ) -> "OcrResultResponse":
        return cls(
            id=result.id,
            job_id=result.job_id,
            content=result.content.content if hasattr(result.content,"content") else str(result.content),
            creation_time=result.creation_time,
        )

class DocumentWithResultResponses(BaseModel):
    id: str
    file_path: str
    file_type: model.FileType
    uploaded_at: datetime
    file_size_bytes: int
    latest_result: OcrResultResponse | None=None
    
    @classmethod
    def from_domain(
        cls,
        document: model.Document,
        result: model.OCRResult | None=None,
    ) -> "DocumentWithResultResponses":
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
            latest_result=(
                OcrResultResponse.from_domain(result) if result else None),
        )
    class Config:
        use_enum_values=False
