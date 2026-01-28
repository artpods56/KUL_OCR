import time


from kul_ocr.domain.model import Document
from kul_ocr.domain.enums import FileType


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
            original_filename="invoice.pdf",
            file_type=FileType.PDF,
            file_path="/uploads/invoice.pdf",
        )

        assert doc.name == "invoice.pdf"
        assert doc.mime_type == "application/pdf"

    def test_document_name_extracted_from_path(self):
        doc = Document(
            original_filename="document.pdf",
            file_type=FileType.PDF,
            file_path="/some/long/path/document.pdf",
        )

        assert doc.name == "document.pdf"

    def test_is_pdf(self):
        pdf = Document(
            original_filename="test.pdf", file_type=FileType.PDF, file_path="/test.pdf"
        )
        png = Document(
            original_filename="test.png", file_type=FileType.PNG, file_path="/test.png"
        )

        assert pdf.is_pdf()
        assert not png.is_pdf()

    def test_is_image(self):
        pdf = Document(
            original_filename="test.pdf", file_type=FileType.PDF, file_path="/test.pdf"
        )
        png = Document(
            original_filename="test.png", file_type=FileType.PNG, file_path="/test.png"
        )

        assert png.is_image()
        assert not pdf.is_image()

    def test_documents_have_unique_timestamps(self):
        doc1 = Document(
            original_filename="a.pdf", file_type=FileType.PDF, file_path="/a.pdf"
        )
        time.sleep(0.01)
        doc2 = Document(
            original_filename="b.pdf", file_type=FileType.PDF, file_path="/b.pdf"
        )

        assert doc1.uploaded_at < doc2.uploaded_at
