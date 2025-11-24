class OCRDomainException(Exception):
    pass


class FileUploadError(OCRDomainException):
    pass


class FileDownloadError(OCRDomainException):
    pass


class UnsupportedFileTypeError(OCRDomainException):
    pass
