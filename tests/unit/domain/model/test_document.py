import time

import pytest

from kul_ocr.domain import model
from kul_ocr.domain.model import Document, FileType


class TestFileType:
    def test_file_type_extension(self):
        assert FileType.PDF.dot_extension == ".pdf"
        assert FileType.PNG.dot_extension == ".png"
        assert FileType.JPG.dot_extension == ".jpg"

    def test_file_type_is_image(self):
        assert FileType.PNG.is_image
        assert FileType.JPG.is_image
        assert not FileType.PDF.is_image


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
