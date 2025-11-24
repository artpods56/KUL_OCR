"""Abstract OCR engine interface and implementations.

This module defines the OCR engine abstraction and concrete implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union, List
import pytesseract
from PIL import Image
from . import config
from pytesseract import Output


@dataclass
class OCRResult:
    """Result from OCR processing.

    Attributes:
        text: Extracted text from the image
        confidence: Average confidence score (0.0 to 100.0)
    """

    text: str
    confidence: float


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

        Configures the path to the Tesseract executable for pytesseract.

        Args:
            tesseract_cmd (str | None): Path to tesseract executable.
                If None, uses the system default path retrieved from config.
        """
        if tesseract_cmd is None:
            tesseract_cmd = config.get_tesseract_path()

        self._tesseract_cmd = tesseract_cmd
        pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

    def process(self, image: Image.Image) -> OCRResult:
        """Extract text from image using Tesseract.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text and average confidence.

        Raises:
            RuntimeError: If Tesseract is not installed or processing fails.
        """
        try:
            data = pytesseract.image_to_data(image, output_type=Output.DICT)

            confidences: List[Union[int, str]] = data.get("conf", [])
            text_words: List[str] = data.get("text", [])

            valid_confidences = [
                float(c)
                for c in confidences
                if isinstance(c, (int, str)) and float(c) != -1.0
            ]

            if valid_confidences:
                avg_confidence = sum(valid_confidences) / len(valid_confidences)
            else:
                avg_confidence = 0.0

            full_text = " ".join(
                word.strip() for word in text_words if word and word.strip()
            )

            return OCRResult(text=full_text, confidence=round(avg_confidence, 2))

        except pytesseract.TesseractNotFoundError as e:
            raise RuntimeError(
                f"Tesseract executable not found at '{self._tesseract_cmd}'. "
                "Please ensure Tesseract is installed and the correct path is configured."
            ) from e

        except Exception as e:
            raise RuntimeError(
                f"OCR processing failed due to an unexpected error: {e}"
            ) from e
