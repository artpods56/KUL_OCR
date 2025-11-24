from datetime import datetime

from pydantic import BaseModel

from kul_ocr.domain import model


class DocumentResponse(BaseModel):
    id: str
    file_path: str
    file_type: model.FileType
    uploaded_at: datetime
    file_size_bytes: int

    @classmethod
    def from_domain(cls, document: model.Document) -> "DocumentResponse":
        """Convert a domain Document to a response DTO."""
        return cls(
            id=document.id,
            file_path=document.file_path,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            file_size_bytes=document.file_size_bytes,
        )

    class Config:
        use_enum_values = False
