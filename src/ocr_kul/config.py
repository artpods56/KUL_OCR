"""Configuration module for OCR service.

This module handles all configuration via environment variables to ensure portability.
NO HARDCODED PATHS ALLOWED - everything must be configurable.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_ = load_dotenv()

# You will have to figure out how to load variables using os module.
# Environment variables should be saved in .env file in the root of the repository.

def get_tesseract_path() -> Path:
    """Get the Tesseract executable path from environment or use system default.

    Environment variable: TESSERACT_PATH
    Default: 'tesseract' (assumes it's in system PATH)

    Returns:
        Path to tesseract executable

    """

    # TODO: Implement environment variable lookup with default fallback
    raise NotImplementedError("TODO: Implement get_tesseract_path()")


def get_data_dir() -> Path:
    """Get the data directory path from environment or use default.

    Environment variable: DATA_DIR
    Default: ./data (relative to project root)

    Returns:
        Path to data directory
    """
    # TODO: Implement environment variable lookup with default fallback
    raise NotImplementedError("TODO: Implement get_data_dir()")


def get_output_dir() -> Path:
    """Get the output directory path from environment or use default.

    Environment variable: OUTPUT_DIR
    Default: ./output

    Returns:
        Path to output directory
    """
    # TODO: Implement and ensure the directory exists
    raise NotImplementedError("TODO: Implement get_output_dir()")
