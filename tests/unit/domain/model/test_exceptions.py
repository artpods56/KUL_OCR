import pytest

from core.domain import exceptions


# ------------------------
# Tests for OCRDomainException
# ------------------------
class TestOCRDomainException:
    """Tests for the base OCRDomainException."""

    def text_inherits_from_exception(self):
        """OCRDomainException should inherit from Exception."""
        assert issubclass(exceptions.DomainException, Exception)

    def test_can_be_raised(self):
        """Should be able to raise OCRDomainException."""
        with pytest.raises(exceptions.DomainException):
            raise exceptions.DomainException("Base error")

    def test_can_be_caught_as_exception(self):
        """Should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise exceptions.DomainException("Base error")

    def test_preserved_error_message(self) -> None:
        """Should preserve the error message."""
        message = "Something went wrong"
        with pytest.raises(exceptions.DomainException, match=message):
            raise exceptions.DomainException(message)

    def test_exception_chaining(self):
        """Should support exception chaining with 'raise from'."""
        original_error = ValueError("Original error")
        with pytest.raises(exceptions.DomainException) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise exceptions.DomainException("Chained error") from e
        assert exc_info.value.__cause__ is original_error


# ------------------------
# Tests for FileUploadError
# ------------------------
class TestFileUploadError:
    """Tests for FileUploadError."""

    def test_inherits_from_exception(self):
        """StorageIOError should inherit from DomainException."""
        assert issubclass(exceptions.StorageIOError, exceptions.DomainException)

    def test_can_be_raised(self):
        """Should be able to raise StorageIOError."""
        with pytest.raises(exceptions.StorageIOError):
            raise exceptions.StorageIOError("Upload failed")

    def test_can_be_caught_as_base_exception(self):
        """Should be catchable as DomainException."""
        with pytest.raises(exceptions.DomainException):
            raise exceptions.StorageIOError("Upload failed")

    def test_preserved_error_message(self) -> None:
        """Should preserve the error message."""
        message = "Failed to upload file.pdf"
        with pytest.raises(exceptions.StorageIOError, match=message):
            raise exceptions.StorageIOError(message)

    def test_can_be_caught_as_exception(self):
        """Should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise exceptions.StorageIOError("Upload failed")

    def test_exception_chaining(self):
        """Should support exception chaining with 'raise from'."""
        original_error = ValueError("Invalid path")
        with pytest.raises(exceptions.StorageIOError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise exceptions.StorageIOError("Upload failed") from e
        assert exc_info.value.__cause__ is original_error

    def test_specific_exception_caught_before_base(self):
        """More specific exceptions should be caught before base exceptions."""
        caught_exception = None
        try:
            raise exceptions.StorageIOError("Upload failed")
        except exceptions.StorageIOError:
            caught_exception = "specific"
        except exceptions.DomainException:
            caught_exception = "base"
        assert caught_exception == "specific"


# ------------------------
# Tests for FileDownloadError
# ------------------------
class TestFileDownloadError:
    """Tests for FileDownloadError."""

    def text_inherits_from_exception(self):
        """FileDownloadError should inherit from OCRDomainException."""
        assert issubclass(exceptions.FileDownloadError, exceptions.DomainException)

    def test_can_be_raised(self):
        """Should be able to raise FileUploadError."""
        with pytest.raises(exceptions.FileDownloadError):
            raise exceptions.FileDownloadError("Download failed")

    def test_can_be_caught_as_base_exception(self):
        """Should be catchable as DomainException."""
        with pytest.raises(exceptions.DomainException):
            raise exceptions.FileDownloadError("file.pdf", "Download failed")

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
        except exceptions.DomainException:
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
            exceptions.UnsupportedFileTypeError, exceptions.DomainException
        )

    def test_can_be_raised(self):
        """Should be able to raise UnsupportedFileTypeError."""
        with pytest.raises(exceptions.UnsupportedFileTypeError):
            raise exceptions.UnsupportedFileTypeError("File type not supported")

    def test_can_be_caught_as_base_exception(self):
        """Should be catchable as OCRDomainException."""
        with pytest.raises(exceptions.DomainException):
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
        except exceptions.DomainException:
            caught_exception = "base"
        assert caught_exception == "specific"
