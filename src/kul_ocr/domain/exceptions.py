class OCRDomainException(Exception):
    pass


class FileUploadError(OCRDomainException):
    pass


class FileDownloadError(OCRDomainException):
    pass


class UnsupportedFileTypeError(OCRDomainException):
    pass


class DocumentNotFoundError(OCRDomainException):
    pass


class DuplicateOCRJobError(OCRDomainException):
    pass
