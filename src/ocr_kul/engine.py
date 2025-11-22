"""Abstract OCR engine interface and implementations.

This module defines the OCR engine abstraction and concrete implementations.
"""
#sorry for stupid errors messages, but...I'm your father
from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image
import pytesseract
from pytesseract import Output, TesseractNotFoundError
from ocr_kul import config
@dataclass
class OCRResult:
    """Result from OCR processing.

    Attributes:
        text: Extracted text from the image
        confidence: Average confidence score (0.0 to 100.0)
    """
    text: str
    # huh what is confidence supposed to be..
    # I don't know...my ego?
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

# there was a TesseractOCREngine class here that was implementation of the OCREngine but not its gone.. how sad..
# write a new one
# no, but yes - fallaut 4
class TesseractOCREngine(OCREngine):
    """Tesseract OCR engine implementation.

    Uses pytesseract to extract text from images.
    """

    def __init__(self, tesseract_cmd: str | None):
        # that arg is either str or None, fill the missing type
        # first I need to find it
        """Initialize Tesseract OCR engine.

        Args:
            tesseract_cmd (str | None): Path to tesseract executable.
                If None, uses system default from config.
        """
        # TODO: Store tesseract_cmd
        # TODO: Import and configure pytesseract.pytesseract.tesseract_cmd
        # Hint: Use config.get_tesseract_path() if tesseract_cmd is None
        if tesseract_cmd is not None:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            pytesseract.pytesseract.tesseract_cmd=config.get_tesseract_path()
            

    def process(self, image:Image.Image) -> OCRResult:
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
        try:
            data=pytesseract.image_to_data(image,Output.DICT)
        except Exception as e:
            raise RuntimeError(f"OCR has fallen, and it's because of you and it: {e}")
        except TesseractNotFoundError:
            raise RuntimeError(
            "Tesseract not found. "
            "Please install Tesseract or provide it's path...or else..."
        )
        text_parts=[]
        for text_item in data['text']:
            if text_item is not None:
                stripped=text.item.strip()
                if stripped!="":
                    text_parts.append(stripped)
        
        text=""
        for part in text_parts:
            if text=="":
                text=part
            else:
                text=text+" "+part
                
        total_confidence=0
        count_confidence=0
        for conf in data['conf']:
            conf_int=int(conf)
            if conf_int != -1:
                total_confidence+=conf_int
                count_confidence+=1
                
        if count_confidence>0:
            avg_confidence=total_confidence/count_confidence
        else:
            avg_confidence=0.0
        return OCRResult(text,avg_confidence)
