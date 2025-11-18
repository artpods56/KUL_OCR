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
    # huh what is confidence supposed to be..
    confidence:


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

# there was a TesseractOCREngine class here that was implementation of the OCREngine but not its gone.. how sad..
# write a new one
    """Tesseract OCR engine implementation.

    Uses pytesseract to extract text from images.
    """

    def __init__(self, tesseract_cmd: = None):
        # that arg is either str or None, fill the missing type
        """Initialize Tesseract OCR engine.

        Args:
            tesseract_cmd (str | None): Path to tesseract executable.
                If None, uses system default from config.
        """
        # TODO: Store tesseract_cmd
        # TODO: Import and configure pytesseract.pytesseract.tesseract_cmd
        # Hint: Use config.get_tesseract_path() if tesseract_cmd is None
        raise NotImplementedError("TODO: Implement __init__")

    def process(self, image:) -> OCRResult:
        #and this one was doing something with a PIL Image
        """Extract text from image using Tesseract.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text and confidence

        Raises:
            RuntimeError: If Tesseract is not installed or processing fails
        """
        # TODO: Implement Tesseract OCR processing
        # 1. Use pytesseract.image_to_data() with Output.DICT
        # 2. Extract text and confidence scores
        # 3. Calculate average confidence (ignore -1 values)
        # 4. Return OCRResult(text=..., confidence=...)
        #
        # Error handling:
        # - Catch pytesseract.TesseractNotFoundError
        # - Raise RuntimeError with helpful message
        raise NotImplementedError("TODO: Implement process()")
