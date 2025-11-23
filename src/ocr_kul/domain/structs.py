from dataclasses import dataclass

from PIL import Image


@dataclass(slots=True)
class PageInput:
    """Standardized input for the OCR engine."""

    image: Image.Image
    page_number: int
    original_document_id: str
