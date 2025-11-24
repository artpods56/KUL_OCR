"""Configuration module for OCR service.

This module handles all configuration via environment variables to ensure portability.
NO HARDCODED PATHS ALLOWED - everything must be configurable.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_ = load_dotenv()


def get_tesseract_path() -> Path:
    """Get the Tesseract executable path from environment or use system default.

    Environment variable: TESSERACT_PATH
    Default: 'tesseract' (assumes it's in system PATH)

    Returns:
        Path to tesseract executable

    """
    tesseract_path = os.getenv("TESSERACT_PATH", "tesseract")
    return Path(tesseract_path)


def get_data_dir() -> Path:
    """Get the data directory path from environment or use default.

    Environment variable: DATA_DIR
    Default: ./data (relative to project root)

    Returns:
        Path to data directory
        >>> get_data_dir()
        Path('data')

    """
    data_dir = os.getenv("DATA_DIR", "data")
    return Path(data_dir)


def get_output_dir() -> Path:
    """Get the output directory path from environment or use default.

    Environment variable: OUTPUT_DIR
    Default: ./output

    Returns:
        Path to output directory

    """
    output_dir = os.getenv("OUTPUT_DIR", "output")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path
