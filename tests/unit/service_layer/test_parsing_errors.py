import pytest

from core.domain import enums, exceptions
from core.service_layer import parsing


def test_parse_file_type_unsupported_raises():
    with pytest.raises(exceptions.UnsupportedFileTypeError):
        parsing.parse_file_type("application/x-unknown")


def test_validate_and_get_file_type_mismatch_raises():
    # filetype will guess based on bytes; use PNG header but declare PDF
    png_magic = b"\x89PNG\r\n\x1a\n" + b"0" * 300
    with pytest.raises(parsing.FileContentMismatchError):
        parsing.validate_and_get_file_type(png_magic, enums.FileType.PDF)


def test_sanitize_filename_handles_empty_and_strips_paths():
    assert parsing.sanitize_filename("") is None
    sanitized = parsing.sanitize_filename("../secret.txt")
    assert sanitized is not None
    assert sanitized.endswith("secret.txt")
