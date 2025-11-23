from pathlib import Path

import pytest


from ocr_kul.domain import model
from ocr_kul.entrypoints import schemas
from tests import factories


class TestDocumentResponse:
    def test_from_domain_converts_all_fields(self, document: model.Document):
        """Test that from_domain converts all Document fields correctly."""
        response = schemas.DocumentResponse.from_domain(document)

        assert response.id == document.id
        assert response.file_path == document.file_path
        assert response.file_type == document.file_type
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

        assert response.file_type == file_type
