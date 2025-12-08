from pathlib import Path
import pytest
from pydantic import ValidationError

from kul_ocr.domain import model
from kul_ocr.entrypoints import schemas
from tests import factories

class TestDocumentResponse:
    """Tests for mapping domain objects to schemas (Happy Path)."""

    def test_from_domain_converts_all_fields(self, document: model.Document):
        """Test that from_domain converts all Document fields correctly."""
        response = schemas.DocumentResponse.from_domain(document)

        assert response.id == document.id
        assert response.file_path == document.file_path
        assert response.file_type == document.file_type.value
        assert response.uploaded_at == document.uploaded_at
        assert response.file_size_bytes == document.file_size_bytes

    @pytest.mark.parametrize(
        "file_type",
        [
            model.FileType.PDF,
            model.FileType.PNG,
            model.FileType.JPEG,
            model.FileType.WEBP,
        ],
    )
    def test_from_domain_with_different_file_types(
        self, file_type: model.FileType, tmp_path: Path
    ):
        document = factories.generate_document(
            file_type=file_type,
            dir_path=tmp_path,
        )

        response = schemas.DocumentResponse.from_domain(document)
        assert response.file_type == file_type.value


class TestDocumentResponseValidation:
    """Tests for validation rules (Error Cases)."""

    VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"
    VALID_DATE = "2024-01-01T12:00:00"
    VALID_PATH = "/tmp/valid_file.pdf"
    VALID_TYPE = "application/pdf"
    VALID_SIZE = 1024

    def test_rejects_invalid_uuid(self):
        with pytest.raises(ValidationError, match="Invalid UUID"):
            schemas.DocumentResponse(
                id="not-a-uuid",
                file_path=self.VALID_PATH,
                file_type=self.VALID_TYPE,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE
            )

    def test_rejects_unsupported_mime_type(self):
        with pytest.raises(ValidationError, match="Unsupported file type"):
            schemas.DocumentResponse(
                id=self.VALID_UUID,
                file_path=self.VALID_PATH,
                file_type="application/exe",
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE
            )

    def test_rejects_negative_file_size(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            schemas.DocumentResponse(
                id=self.VALID_UUID,
                file_path=self.VALID_PATH,
                file_type=self.VALID_TYPE,
                file_size_bytes=-50,
                uploaded_at=self.VALID_DATE
            )

    def test_rejects_path_traversal(self):
        with pytest.raises(ValidationError, match="traversal characters"):
            schemas.DocumentResponse(
                id=self.VALID_UUID,
                file_path="../../etc/passwd",
                file_type=self.VALID_TYPE,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE
            )

    def test_rejects_empty_file_path(self):
        with pytest.raises(ValidationError, match="empty"):
            schemas.DocumentResponse(
                id=self.VALID_UUID,
                file_path="   ",
                file_type=self.VALID_TYPE,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE
            )