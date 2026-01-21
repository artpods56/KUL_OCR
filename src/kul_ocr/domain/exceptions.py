class DomainException(Exception):
    """Base exception for all domain-related errors."""

    pass


# Alias for backward compatibility in tests
OCRDomainException = DomainException


class FileUploadError(DomainException):
    """Raised when a file upload operation fails."""

    def __init__(self, file_path: str, message: str | None = None):
        self.file_path = file_path
        self.message = message or f"Failed to upload file to: {file_path}"
        super().__init__(self.message)


class FileDownloadError(DomainException):
    """Raised when a file download operation fails."""

    def __init__(self, file_path: str, message: str | None = None):
        self.file_path = file_path
        self.message = message or f"Failed to download file from: {file_path}"
        super().__init__(self.message)


class UnsupportedFileTypeError(DomainException):
    """Raised when an unsupported file type is provided."""

    def __init__(self, file_type: str, message: str | None = None):
        self.file_type = file_type
        self.message = message or f"Unsupported file type: {file_type}"
        super().__init__(self.message)


class FileExtensionMismatchError(DomainException):
    """Raised when file extension doesn't match declared file type."""

    def __init__(
        self, expected_extension: str, actual_extension: str, message: str | None = None
    ):
        self.expected_extension = expected_extension
        self.actual_extension = actual_extension
        self.message = message or (
            f"File extension mismatch: expected {expected_extension}, "
            f"got {actual_extension}"
        )
        super().__init__(self.message)


class DocumentNotFoundError(DomainException):
    """Raised when a document cannot be found."""

    def __init__(self, document_id: str, message: str | None = None):
        self.document_id = document_id
        self.message = message or f"Document not found: {document_id}"
        super().__init__(self.message)


class OCRJobNotFoundError(DomainException):
    """Raised when an OCR job cannot be found."""

    def __init__(self, job_id: str, message: str | None = None):
        self.job_id = job_id
        self.message = message or f"OCR job not found: {job_id}"
        super().__init__(self.message)


class DuplicateOCRJobError(DomainException):
    """Raised when a duplicate OCR job is submitted for the same document."""

    def __init__(
        self, document_id: str, job_id: str | None = None, message: str | None = None
    ):
        self.document_id = document_id
        self.job_id = job_id
        self.message = message or (
            f"Document {document_id} already has a pending or active job"
            + (f": {job_id}" if job_id else "")
        )
        super().__init__(self.message)


class InvalidJobStatusTransitionError(DomainException):
    """Raised when a job status transition is invalid."""

    def __init__(
        self,
        job_id: str,
        current_status: str,
        attempted_status: str,
        message: str | None = None,
    ):
        self.job_id = job_id
        self.current_status = current_status
        self.attempted_status = attempted_status
        self.message = message or (
            f"Invalid status transition for job {job_id}: "
            f"{current_status} -> {attempted_status}"
        )
        super().__init__(self.message)


class UnknownJobStatusError(DomainException):
    """Raised when an unknown job status is encountered."""

    def __init__(self, status: str, message: str | None = None):
        self.status = status
        self.message = message or f"Unknown job status {status}."
        super().__init__(self.message)
