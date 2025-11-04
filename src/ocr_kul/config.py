import os

SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
DEFAULT_OUTPUT_DIR = 'output'
DEFAULT_LANG = 'eng'
DEFAULT_TIMEOUT = 30 #s

DEFAULT_TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

TESSERACT_CMD = os.getenv('TESSERACT_CMD', DEFAULT_TESSERACT_PATH)