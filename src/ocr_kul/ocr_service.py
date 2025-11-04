import time
import logging
from pathlib import Path
from typing import List, Dict, Any, TypedDict
from datetime import datetime
import pytesseract
from PIL import Image
from src.ocr_kul.config import DEFAULT_LANG, DEFAULT_TIMEOUT, TESSERACT_CMD

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(ch)


class ImageResult(TypedDict):
    filename: str
    filepath: str
    text: str
    processing_time: float
    status: str
    error: str | None


class BatchResult(TypedDict):
    metadata: Dict[str, Any]
    results: List[ImageResult]


class OcrService:
    def __init__(self, lang: str = DEFAULT_LANG, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.lang: str = lang
        self.timeout: int = timeout
        self._setup_tesseract()
        self._validate_tesseract()

    def _setup_tesseract(self) -> None:
        if TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            logger.info(f"Using Tesseract from: {TESSERACT_CMD}")

    def _validate_tesseract(self) -> None:
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
        except Exception as e:
            raise RuntimeError(
                "Tesseract is not installed or not accessible.\n"
                f"TESSERACT_CMD: {TESSERACT_CMD}\n"
                f"Error: {e}"
            )

    def process_image(self, image_path: Path) -> ImageResult:
        start_time = time.time()

        try:
            with Image.open(image_path) as image:
                text: str = pytesseract.image_to_string(
                    image,
                    lang=self.lang,
                    timeout=self.timeout
                )

            processing_time: float = time.time() - start_time

            return {
                'filename': image_path.name,
                'filepath': str(image_path.absolute()),
                'text': text.strip(),
                'processing_time': round(processing_time, 3),
                'status': 'success',
                'error': None
            }

        except RuntimeError as e:
            return {
                'filename': image_path.name,
                'filepath': str(image_path.absolute()),
                'text': '',
                'processing_time': round(time.time() - start_time, 3),
                'status': 'error',
                'error': f"Timeout after {self.timeout}s: {str(e)}"
            }
        except Exception as e:
            return {
                'filename': image_path.name,
                'filepath': str(image_path.absolute()),
                'text': '',
                'processing_time': round(time.time() - start_time, 3),
                'status': 'error',
                'error': str(e)
            }

    def process_batch(self, image_paths: List[Path]) -> BatchResult:
        results: List[ImageResult] = []
        total_start = time.time()

        logger.info(f"\nStarting processing of {len(image_paths)} images")

        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"[{i}/{len(image_paths)}] Processing: {image_path.name}")
            result = self.process_image(image_path)
            results.append(result)

            if result['status'] == 'success':
                preview = result['text'][:50].replace('\n', ' ')
                logger.info(f"OK | Preview: {preview}...")
            else:
                logger.error(f"ERROR | {result['error']}")

        total_time = time.time() - total_start
        successful = sum(1 for r in results if r['status'] == 'success')

        return {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_images': len(results),
                'successful': successful,
                'failed': len(results) - successful,
                'language': self.lang,
                'tesseract_version': str(pytesseract.get_tesseract_version()),
                'total_processing_time': round(total_time, 3)
            },
            'results': results
        }
