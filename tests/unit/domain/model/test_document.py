import time

import pytest

from kul_ocr.domain import model
from kul_ocr.domain.model import Document, FileType, SimpleOCRValue, MultiPageOcrValue


class TestFileType:
    def test_file_type_extension(self):
        assert FileType.PDF.dot_extension == ".pdf"
        assert FileType.PNG.dot_extension == ".png"
        assert FileType.JPG.dot_extension == ".jpg"

    def test_file_type_is_image(self):
        assert FileType.PNG.is_image
        assert FileType.JPG.is_image
        assert not FileType.PDF.is_image

    @pytest.mark.parametrize(
        "file_type,expected_value_class",
        [
            (FileType.PDF, MultiPageOcrValue),
            (FileType.PNG, SimpleOCRValue),
            (FileType.JPG, SimpleOCRValue),
            (FileType.JPEG, SimpleOCRValue),
            (FileType.WEBP, SimpleOCRValue),
        ],
    )
    def test_get_value_class_returns_correct_type(
        self, file_type: model.FileType, expected_value_class: type[model.OCRValueTypes]
    ):
        assert file_type.get_value_class() == expected_value_class

    def test_pdf_returns_multipage_value(self):
        """PDF files should always return MultiPageOcrValue, even for single-page PDFs."""
        assert FileType.PDF.get_value_class() == MultiPageOcrValue

    def test_all_image_types_return_simple_value(self):
        """All image file types should return SimpleOCRValue."""
        image_types = [FileType.PNG, FileType.JPG, FileType.JPEG, FileType.WEBP]
        for file_type in image_types:
            assert file_type.get_value_class() == SimpleOCRValue


class TestDocument:
    def test_document_creation(self):
        doc = Document(
            id="doc-1", file_path="/uploads/invoice.pdf", file_type=FileType.PDF
        )

        assert doc.id == "doc-1"
        assert doc.name == "invoice.pdf"
        assert doc.mime_type == "application/pdf"

    def test_document_name_extracted_from_path(self):
        doc = Document(
            id="doc-1", file_path="/some/long/path/document.pdf", file_type=FileType.PDF
        )

        assert doc.name == "document.pdf"

    def test_is_pdf(self):
        pdf = Document(id="1", file_path="/test.pdf", file_type=FileType.PDF)
        png = Document(id="2", file_path="/test.png", file_type=FileType.PNG)

        assert pdf.is_pdf()
        assert not png.is_pdf()

    def test_is_image(self):
        pdf = Document(id="1", file_path="/test.pdf", file_type=FileType.PDF)
        png = Document(id="2", file_path="/test.png", file_type=FileType.PNG)

        assert png.is_image()
        assert not pdf.is_image()

    def test_documents_have_unique_timestamps(self):
        doc1 = Document(id="1", file_path="/a.pdf", file_type=FileType.PDF)
        time.sleep(0.01)
        doc2 = Document(id="2", file_path="/b.pdf", file_type=FileType.PDF)

        assert doc1.uploaded_at < doc2.uploaded_at
