import re
from pathlib import Path

import filetype

import kul_ocr.domain.model
from kul_ocr.domain import model, enums, exceptions
from kul_ocr.domain.exceptions import DomainException

# Minimum bytes needed for reliable file type detection (filetype needs max 261)
MIN_MAGIC_BYTES = 261


def parse_file_type(content_type: str | None) -> enums.FileType:
    if content_type is None:
        content_type = ""
    try:
        return enums.FileType(content_type)
    except ValueError:
        raise exceptions.UnsupportedFileTypeError(
            f"Unsupported file type: {content_type}"
        )


def get_mime_from_bytes(file_bytes: bytes) -> str:
    """Get mime of a file using filetype library.

    Args:
        file_bytes: The byte string of the file to get the mime type of.

    Returns:
        str: mime type in format like `application/pdf`

    """
    kind = filetype.guess(file_bytes)
    if kind is None:
        raise ValueError(
            "Could not detect file type from bytes object",
        )
    return kind.mime


def validate_and_get_file_type(
    file_bytes: bytes, declared_type: enums.FileType
) -> None:
    """Validate that file content matches the declared file type using magic bytes.

    Args:
        file_bytes: The first bytes of the file (at least 261 bytes).
        declared_type: The file type declared by the client.

    Raises:
        FileContentMismatchError: If the detected content type doesn't match.
    """
    kind = filetype.guess(file_bytes)

    if kind is None:
        raise FileContentMismatchError(
            declared_type=declared_type.value,
            detected_type="unknown (could not detect file type)",
        )

    detected_mime = kind.mime
    expected_mime = declared_type.value

    # Both are normalized to image/jpeg by filetype
    if detected_mime != expected_mime:
        raise FileContentMismatchError(
            declared_type=expected_mime,
            detected_type=detected_mime,
        )

    return kind


def sanitize_filename(filename: str | None) -> str | None:
    """Sanitize a filename for safe storage and display.

    - Extracts only the filename (no path components)
    - Removes path traversal characters
    - Normalizes unicode characters
    - Replaces unsafe characters with underscores
    - Preserves the file extension

    Args:
        filename: The original filename from the client upload.

    Returns:
        Sanitized filename suitable for display/storage metadata,
        or None if input was None/empty.
    """
    if not filename or not filename.strip():
        return None

    name = filename.strip()

    name = Path(name).name

    name = name.encode("utf-8", errors="replace").decode("utf-8")

    name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", name)

    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", name)

    name = re.sub(r"\.{2,}", ".", name)

    name = name.strip(". ")

    if not name:
        return None

    max_length = 255
    if len(name) > max_length:
        stem = Path(name).stem[: max_length - 40]
        ext = Path(name).suffix
        name = stem[: max_length - len(ext) - 1] + ext if ext else stem

    return name


class FileContentMismatchError(DomainException):
    code: str = "FILE_CONTENT_MISMATCH"

    def __init__(
        self,
        declared_type: str,
        detected_type: str,
        message: str | None = None,
    ):
        msg = message or (
            f"File content mismatch: declared as {declared_type}, "
            f"but content appears to be {detected_type}"
        )
        super().__init__(
            message=msg,
            declared_type=declared_type,
            detected_type=detected_type,
        )
