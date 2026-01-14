from dataclasses import dataclass

from PIL import Image

from kul_ocr.domain.model import FileType


@dataclass(slots=True)
class PageInput:
    """Standardized input for the OCR engine."""

    image: Image.Image
    page_number: int
    original_document_id: str


@dataclass(slots=True, frozen=True)
class DocumentInput:
    """Minimal document data for OCR processing - no ORM dependencies."""

    id: str
    file_path: str
    file_type: FileType
