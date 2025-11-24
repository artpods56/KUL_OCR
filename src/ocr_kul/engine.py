"""Abstract OCR engine interface and implementations.

This module defines the OCR engine abstraction and concrete implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


@dataclass
class OCRResult:
    """Result from OCR processing.

    Attributes:
        text: Extracted text from the image
        confidence: Average confidence score (0.0 to 100.0)
    """

    text: str
    confidence: float  # Average confidence score from OCR


class OCREngine(ABC):
    """Abstract base class for OCR engines.

    All OCR implementations must inherit from this class and implement
    the process() method.
    """

    @abstractmethod
    def process(self, image: Image.Image) -> OCRResult:
        """Process an image and extract text.

        Args:
            image: PIL Image object to process

        Returns:
            OCRResult containing extracted text and confidence score

        Raises:
            RuntimeError: If OCR processing fails
        """
        pass


class TesseractOCREngine(OCREngine):
    """Tesseract OCR engine implementation.

    Uses pytesseract to extract text from images.
    """

    def __init__(self, tesseract_cmd: str | None = None):
        """Initialize Tesseract OCR engine.

        Args:
            tesseract_cmd (str | None): Path to tesseract executable.
                If None, uses system default from config.
        """
        # 1. Store tesseract_cmd
        self.tesseract_cmd = tesseract_cmd

        # 2. Import and configure pytesseract.pytesseract.tesseract_cmd
        from ocr_kul.config import get_tesseract_path
        import pytesseract

        if self.tesseract_cmd is None:
            pytesseract.pytesseract.tesseract_cmd = str(get_tesseract_path())
        else:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def process(self, image: Image.Image) -> OCRResult:
        """Extract text from image using Tesseract.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text and confidence

        Raises:
            RuntimeError: If Tesseract is not installed or processing fails
        """
        import pytesseract

        try:
            # 1. Use pytesseract.image_to_data() with Output.DICT
            output = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )

            # 2. Extract text and confidence scores
            text_list = output["text"]

            # 3. Calculate average confidence (ignore -1 values)
            conf_list = [int(c) for c in output["conf"] if int(c) != -1]

            average_confidence = sum(conf_list) / len(conf_list) if conf_list else 0.0
            text = " ".join(text_list).strip()

            # 4. Return OCRResult(text=..., confidence=...)
            return OCRResult(text=text, confidence=average_confidence)

        # Error handling:
        # - Catch pytesseract.TesseractNotFoundError
        except pytesseract.TesseractNotFoundError as e:
            raise RuntimeError(
                "Tesseract executable not found. Please install Tesseract OCR."
            ) from e

        # - Raise RuntimeError with helpful message
        except Exception as e:
            raise RuntimeError("OCR processing failed.") from e
