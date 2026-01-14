class DomainException(Exception):
    """Base exception for all domain-related errors."""

    pass


# Alias for backward compatibility in tests
OCRDomainException = DomainException


class FileUploadError(DomainException):
    """Raised when a file upload operation fails."""

    pass


class FileDownloadError(DomainException):
    """Raised when a file download operation fails."""

    pass


class UnsupportedFileTypeError(DomainException):
    """Raised when an unsupported file type is provided."""

    pass


class DocumentNotFoundError(DomainException):
    """Raised when a document cannot be found."""

    pass


class OCRJobNotFoundError(DomainException):
    """Raised when an OCR job cannot be found."""

    pass


class DuplicateOCRJobError(DomainException):
    """Raised when a duplicate OCR job is submitted for the same document."""

    pass


class InvalidJobStatusError(DomainException):
    """Raised when a job status transition is invalid."""

    pass
