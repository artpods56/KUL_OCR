from pathlib import Path

from core.domain import enums, exceptions


def validate_file_extension(file_type: enums.FileType, filename: str) -> None:
    """Validate that filename extension matches the expected file type.

    Args:
        file_type: The expected file type.
        filename: Name of the file to validate.

    Raises:
        FileExtensionMismatchError: If extension doesn't match.
    """
    if not filename:
        return

    actual_extension = Path(filename).suffix.lower()
    if actual_extension and actual_extension != file_type.dot_extension:
        raise exceptions.FileExtensionMismatchError(
            expected_extension=file_type.dot_extension,
            actual_extension=actual_extension,
        )


def validate_mime_type(file_type: enums.FileType, mime_type: str) -> None:
    """Validate that MIME type matches the expected file type.

    Args:
        file_type: The expected file type.
        mime_type: The actual MIME type to validate.

    Raises:
        FileContentMissmatchError: If MIME type doesn't match.
    """
    if file_type.value != mime_type:
        raise exceptions.FileContentMissmatchError(
            expected_mime=file_type.value,
            actual_mime=mime_type,
        )


def validate_file_size(file_size: int, max_bytes: int) -> None:
    if file_size > max_bytes:
        raise exceptions.FileSizeExceededError(
            file_size=file_size,
            max_bytes=max_bytes,
        )
