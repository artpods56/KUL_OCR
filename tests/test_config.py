"""Tests for configuration module."""

import os
from pathlib import Path


def test_get_tesseract_path_returns_path_type() -> None:
    """get_tesseract_path must return a Path object."""
    from ocr_kul.config import get_tesseract_path

    result = get_tesseract_path()
    assert isinstance(result, Path), "Must return Path object, not string"


def test_get_tesseract_path_uses_env_variable() -> None:
    """get_tesseract_path must respect TESSERACT_PATH environment variable."""
    from ocr_kul.config import get_tesseract_path

    # Set custom path
    os.environ["TESSERACT_PATH"] = "/custom/tesseract"
    result = get_tesseract_path()

    assert result == Path("/custom/tesseract"), (
        "Must use TESSERACT_PATH environment variable when set"
    )

    # Cleanup
    del os.environ["TESSERACT_PATH"]


def test_get_tesseract_path_has_default() -> None:
    """get_tesseract_path must have a sensible default when env var not set."""
    import os

    from ocr_kul.config import get_tesseract_path

    # Ensure env var is not set
    os.environ.pop("TESSERACT_PATH", None)

    result = get_tesseract_path()
    assert result is not None, "Must return a default value"
    assert isinstance(result, Path)


def test_get_data_dir_returns_path_type() -> None:
    """get_data_dir must return a Path object."""
    from ocr_kul.config import get_data_dir

    result = get_data_dir()
    assert isinstance(result, Path), "Must return Path object, not string"


def test_get_data_dir_uses_env_variable() -> None:
    """get_data_dir must respect DATA_DIR environment variable."""
    from ocr_kul.config import get_data_dir

    os.environ["DATA_DIR"] = "/custom/data"
    result = get_data_dir()

    assert result == Path("/custom/data")

    del os.environ["DATA_DIR"]


def test_get_output_dir_returns_path_type() -> None:
    """get_output_dir must return a Path object."""
    from ocr_kul.config import get_output_dir

    result = get_output_dir()
    assert isinstance(result, Path)


def test_get_output_dir_creates_directory() -> None:
    """get_output_dir must create the directory if it doesn't exist."""
    import tempfile

    from ocr_kul.config import get_output_dir

    with tempfile.TemporaryDirectory() as tmpdir:
        test_output = Path(tmpdir) / "test_output"
        os.environ["OUTPUT_DIR"] = str(test_output)

        result = get_output_dir()

        assert result.exists(), "Output directory must be created"
        assert result.is_dir(), "Must be a directory"

        del os.environ["OUTPUT_DIR"]
