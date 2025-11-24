from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, cast
from pathlib import Path
import pytesseract
from PIL import Image
from . import config
from pytesseract import Output


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float


class OCREngine(ABC):
    @abstractmethod
    def process(self, image: Image.Image) -> OCRResult:
        pass


class TesseractOCREngine(OCREngine):
    _tesseract_cmd: str | None

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        if tesseract_cmd is None:
            path_object: Path = config.get_tesseract_path()
            tesseract_cmd = str(path_object)

        self._tesseract_cmd = tesseract_cmd
        pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd

    def process(self, image: Image.Image) -> OCRResult:
        try:
            data = pytesseract.image_to_data(image, output_type=Output.DICT)

            confidences: List[int] = cast(List[int], data.get("conf", []))
            text_words: List[str] = cast(List[str], data.get("text", []))

            valid_confidences: List[float] = [float(c) for c in confidences if c != -1]

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
