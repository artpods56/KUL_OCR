from multiprocessing import Value
import pytest
from kul_ocr.domain import exceptions
# ------------------------
# Tests for OCRDomainException
# ------------------------
class TestOCRDomainException:
    """Tests for the base OCRDomainException."""
    def text_inherits_from_exception(self):
        """OCRDomainException should inherit from Exception."""
        assert issubclass(exceptions.OCRDomainException, Exception)
    def test_can_be_raised(self):
        """Should be able to raise OCRDomainException."""
        with pytest.raises(exceptions.OCRDomainException):
            raise exceptions.OCRDomainException("Base error")
    def test_can_be_caught_as_exception(self):
        """Should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise exceptions.OCRDomainException("Base error")
    def test_preserved_error_message(self) -> None:
        """Should preserve the error message."""
        message = "Something went wrong"
        with pytest.raises(exceptions.OCRDomainException, match=message):
            raise exceptions.OCRDomainException(message)
    def test_exception_chaining(self):
        """Should support exception chaining with 'raise from'."""
        original_error = ValueError("Original error")
        with pytest.raises(exceptions.OCRDomainException) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise exceptions.OCRDomainException("Chained error") from e
        assert exc_info.value.__cause__ is original_error
# ------------------------
# Tests for FileUploadError
# ------------------------
class TestFileUploadError:
    """Tests for FileUploadError."""
    def text_inherits_from_exception(self):
        """FileUploadError should inherit from OCRDomainException."""
        assert issubclass(exceptions.FileDownloadError, exceptions.OCRDomainException)
    def test_can_be_raised(self):
        """Should be able to raise FileUploadError."""
        with pytest.raises(exceptions.FileUploadError):
            raise exceptions.FileUploadError("Upload failed")
    def test_can_be_caught_as_base_exception(self):
        """Should be catchable as OCRDomainException."""
        with pytest.raises(exceptions.OCRDomainException):
            raise exceptions.FileUploadError("Upload failed")
    def test_preserved_error_message(self) -> None:
        """Should preserve the error message."""
        message = "Failed to upload file.pdf"
        with pytest.raises(exceptions.FileUploadError, match=message):
            raise exceptions.FileUploadError(message)
    def test_can_be_caught_as_exception(self):
        """Should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise exceptions.FileUploadError("Upload failed")
    def test_exception_chaining(self):
        """Should support exception chaining with 'raise from'."""
        original_error = ValueError("Invalid path")
        with pytest.raises(exceptions.FileUploadError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise exceptions.FileUploadError("Upload failed") from e
        assert exc_info.value.__cause__ is original_error
    def test_specific_exception_cauth_before_base(self):
        """More specific exceptions should be cauth before base exceptions."""
        caught_exception = None
        try:
            raise exceptions.FileUploadError("Upload failed")
        except exceptions.FileUploadError:
            caught_exception = "specific"
        except exceptions.OCRDomainException:
            caught_exception = "base"
        assert caught_exception == "specific"
# ------------------------
# Tests for FileDownloadError
# ------------------------
class TestFileDownloadError:
    """Tests for FileDownloadError."""
    def text_inherits_from_exception(self):
        """FileDownloadError should inherit from OCRDomainException."""
        assert issubclass(exceptions.FileDownloadError, exceptions.OCRDomainException)
    def test_can_be_raised(self):
        """Should be able to raise FileUploadError."""
        with pytest.raises(exceptions.FileDownloadError):
            raise exceptions.FileDownloadError("Download failed")
    def test_can_be_caught_as_base_exception(self):
        """Should be catchable as OCRDomainException."""
        with pytest.raises(exceptions.OCRDomainException):
            raise exceptions.FileUploadError("Upload failed")
    def test_preserved_error_message(self) -> None:
        """Should preserve the error message."""
        message = "Failed to download file.pdf"
        with pytest.raises(exceptions.FileDownloadError, match=message):
            raise exceptions.FileDownloadError(message)
    def test_can_be_caught_as_exception(self):
        """Should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise exceptions.FileDownloadError("Download failed")
    def test_exception_chaining(self):
        """Should support exception chaining with 'raise from'."""
        original_error = ValueError("Disc error")
        with pytest.raises(exceptions.FileDownloadError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise exceptions.FileDownloadError("Dounload failed") from e
        assert exc_info.value.__cause__ is original_error
    def test_specific_exception_cauth_before_base(self):
        """More specific exceptions should be cauth before base exceptions."""
        caught_exception = None
        try:
            raise exceptions.FileDownloadError("Download failed")
        except exceptions.FileDownloadError:
            caught_exception = "specific"
        except exceptions.OCRDomainException:
            caught_exception = "base"
        assert caught_exception == "specific"
# ------------------------
# Tests for UnsupportedFileTypeError
# ------------------------
class TestUnsupportedFileTypeError:
    """Tests for UnsupportedFileTypeError."""
    def text_inherits_from_exception(self):
        """UnsupportedFileTypeError should inherit from OCRDomainException."""
        assert issubclass(
            exceptions.UnsupportedFileTypeError, exceptions.OCRDomainException
        )
    def test_can_be_raised(self):
        """Should be able to raise UnsupportedFileTypeError."""
        with pytest.raises(exceptions.UnsupportedFileTypeError):
            raise exceptions.UnsupportedFileTypeError("File type not supported")
    def test_can_be_caught_as_base_exception(self):
        """Should be catchable as OCRDomainException."""
        with pytest.raises(exceptions.OCRDomainException):
            raise exceptions.UnsupportedFileTypeError("File type not supported")
    def test_preserved_error_message(self) -> None:
        """Should preserve the error message."""
        message = "Unsupported file type: .exe"
        with pytest.raises(exceptions.UnsupportedFileTypeError, match=message):
            raise exceptions.UnsupportedFileTypeError(message)
    def test_can_be_caught_as_exception(self):
        """Should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise exceptions.UnsupportedFileTypeError("File type not supported")
    def test_exception_chaining(self):
        """Should support exception chaining with 'raise from'."""
        original_error = ValueError("Wrong type")
        with pytest.raises(exceptions.UnsupportedFileTypeError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise exceptions.UnsupportedFileTypeError(
                    "File type not supported"
                ) from e
        assert exc_info.value.__cause__ is original_error
    def test_specific_exception_cauth_before_base(self):
        """More specific exceptions should be cauth before base exceptions."""
        caught_exception = None
        try:
            raise exceptions.UnsupportedFileTypeError("File type not supported")
        except exceptions.UnsupportedFileTypeError:
            caught_exception = "specific"
        except exceptions.OCRDomainException:
            caught_exception = "base"
        assert caught_exception == "specific"