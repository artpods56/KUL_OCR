import os
from typing import List

SUPPORTED_FORMATS: List[str] = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
DEFAULT_OUTPUT_DIR: str = 'output'
DEFAULT_LANG: str = 'eng'
DEFAULT_TIMEOUT: int = 30
DEFAULT_TESSERACT_PATH: str = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSERACT_CMD: str = os.getenv('TESSERACT_CMD', DEFAULT_TESSERACT_PATH)
