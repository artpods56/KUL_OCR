from kul_ocr.exceptions import DomainException

# Alias for backward compatibility in tests
OCRDomainException = DomainException


class FileDownloadError(DomainException):
    code: str = "FILE_DOWNLOAD_FAILED"

    def __init__(self, file_path: str, message: str | None = None):
        msg = message or f"Failed to download file from: {file_path}"
        super().__init__(message=msg, file_path=file_path)


class FileSizeExceededError(DomainException):
    code: str = "FILE_SIZE_EXCEEDED"

    def __init__(self, file_size: int, max_bytes: int, message: str | None = None):
        msg = (
            message
            or f"File size {file_size} bytes exceeds maximum allowed size of {max_bytes} bytes"
        )
        super().__init__(message=msg, file_size=file_size, max_bytes=max_bytes)
