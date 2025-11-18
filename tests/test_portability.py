"""Test suite for code portability.

These tests ensure the code can run on different systems without hardcoded paths.
"""

from pathlib import Path


def test_no_hardcoded_windows_paths() -> None:
    """Ensure no hardcoded Windows paths exist in source code."""
    src_files = list(Path("src").rglob("*.py"))

    for file in src_files:
        content = file.read_text()
        assert "C:\\" not in content, f"Hardcoded Windows path found in {file}"
        assert "D:\\" not in content, f"Hardcoded Windows path found in {file}"


def test_no_hardcoded_unix_paths() -> None:
    """Ensure no hardcoded Unix/Linux paths exist in source code."""
    src_files = list(Path("src").rglob("*.py"))

    hardcoded_patterns = ["/home/", "/Users/", "/content/", "/tmp/data"]

    for file in src_files:
        content = file.read_text()
        for pattern in hardcoded_patterns:
            assert pattern not in content, (
                f"Hardcoded Unix path '{pattern}' found in {file}"
            )


def test_config_module_exists() -> None:
    """Config module must exist and be importable."""
    from ocr_kul import config

    assert config is not None
    assert hasattr(config, "get_tesseract_path")
    assert hasattr(config, "get_data_dir")


def test_config_uses_environment_variables() -> None:
    """Configuration must use environment variables with sensible defaults."""
    import os

    from ocr_kul import config

    # Test tesseract path configuration
    default_path = config.get_tesseract_path()
    assert default_path is not None, "get_tesseract_path() must return a value"

    # Test that env variable is respected
    os.environ["TESSERACT_PATH"] = "/custom/tesseract"
    custom_path = config.get_tesseract_path()
    assert custom_path == Path("/custom/tesseract"), (
        "Config must respect TESSERACT_PATH environment variable"
    )

    # Cleanup
    del os.environ["TESSERACT_PATH"]


def test_data_dir_is_portable() -> None:
    """Data directory must be configurable via environment variable."""
    import os

    from ocr_kul import config

    # Test default exists
    default_dir = config.get_data_dir()
    assert default_dir is not None
    assert isinstance(default_dir, Path)

    # Test environment variable override
    os.environ["DATA_DIR"] = "/custom/data"
    custom_dir = config.get_data_dir()
    assert custom_dir == Path("/custom/data")

    # Cleanup
    del os.environ["DATA_DIR"]


def test_paths_use_pathlib() -> None:
    """All path operations must use pathlib.Path, not string concatenation."""
    from ocr_kul import config

    tesseract_path = config.get_tesseract_path()
    data_dir = config.get_data_dir()

    assert isinstance(tesseract_path, Path), "get_tesseract_path must return Path"
    assert isinstance(data_dir, Path), "get_data_dir must return Path"
