from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from backend.documents import schema
from core.domain import model, enums
from tests import factories


class TestDocumentResponse:
    """Tests for mapping domain objects to schemas (Happy Path)."""

    def test_from_domain_converts_all_fields(self, document: model.Document):
        """Test that from_domain converts all Document fields correctly."""
        response = schema.DocumentResponse.from_domain(document)

        assert str(response.id) == document.id
        assert response.file_path == document.file_path
        assert response.file_type == document.file_type.value
        assert response.uploaded_at == document.uploaded_at
        assert response.file_size_bytes == document.file_size_bytes

    @pytest.mark.parametrize(
        "file_type",
        [
            enums.FileType.PDF,
            enums.FileType.PNG,
            enums.FileType.JPEG,
            enums.FileType.WEBP,
        ],
    )
    def test_from_domain_with_different_file_types(
        self, file_type: enums.FileType, tmp_path: Path
    ):
        document = factories.generate_document(
            file_type=file_type,
            dir_path=tmp_path,
        )

        response = schema.DocumentResponse.from_domain(document)
        assert response.file_type == file_type.value


class SampleEnum(Enum):
    TEST = "test"


class TestDocumentResponseValidation:
    """Tests for validation rules (Error Cases)."""

    VALID_UUID = UUID("550e8400-e29b-41d4-a716-446655440000")
    VALID_DATE = datetime(
        year=2022, month=1, day=1, hour=12, minute=0, second=0, tzinfo=None
    )
    VALID_PATH = "/tmp/valid_file.pdf"
    VALID_FILENAME = "document.pdf"
    VALID_TYPE = enums.FileType.PDF
    VALID_SIZE = 1024

    INVALID_ENUM = SampleEnum.TEST

    def test_rejects_invalid_uuid(self):
        with pytest.raises((ValidationError, ValueError), match="UUID"):
            schema.DocumentResponse(
                id=UUID("not-a-uuid"),
                original_filename=self.VALID_FILENAME,
                file_type=self.VALID_TYPE,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE,
                file_path=self.VALID_PATH,
            )

    def test_rejects_unsupported_mime_type(self):
        with pytest.raises(ValidationError, match="validation error"):
            schema.DocumentResponse(
                id=self.VALID_UUID,
                original_filename=self.VALID_FILENAME,
                file_type=self.INVALID_ENUM,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE,
                file_path=self.VALID_PATH,
            )

    def test_rejects_negative_file_size(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            schema.DocumentResponse(
                id=self.VALID_UUID,
                original_filename=self.VALID_FILENAME,
                file_type=self.VALID_TYPE,
                file_size_bytes=-50,
                uploaded_at=self.VALID_DATE,
                file_path=self.VALID_PATH,
            )

    def test_rejects_path_traversal_in_file_path(self):
        with pytest.raises(ValidationError, match="traversal characters"):
            schema.DocumentResponse(
                id=self.VALID_UUID,
                original_filename=self.VALID_FILENAME,
                file_type=self.VALID_TYPE,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE,
                file_path="../../etc/passwd",
            )

    def test_rejects_empty_original_filename(self):
        with pytest.raises(ValidationError, match="empty"):
            schema.DocumentResponse(
                id=self.VALID_UUID,
                original_filename="   ",
                file_type=self.VALID_TYPE,
                file_size_bytes=self.VALID_SIZE,
                uploaded_at=self.VALID_DATE,
                file_path=self.VALID_PATH,
            )
