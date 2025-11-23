from pathlib import Path

import pytest
from PIL import Image

from ocr_kul.adapters.loaders.filesystem import FileSystemDocumentLoader
from ocr_kul.domain import model
from tests import factories


@pytest.fixture
def loader() -> FileSystemDocumentLoader:
    return FileSystemDocumentLoader()


@pytest.fixture
def image_file(tmp_path: Path) -> Path:
    """Create a simple test image."""
    image_path = tmp_path / "test_image.png"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(image_path)
    return image_path


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    """Create a simple test PDF with 2 pages."""
    import pymupdf

    pdf_path = tmp_path / "test.pdf"
    doc = pymupdf.open()

    for _ in range(2):
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Test content")

    doc.save(pdf_path)
    doc.close()
    return pdf_path


class TestFileSystemDocumentLoader:
    def test_load_single_image_returns_one_page(
        self, loader: FileSystemDocumentLoader, image_file: Path, tmp_path: Path
    ):
        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PNG
        )
        document.file_path = str(image_file)

        pages = list(loader.load_pages(document))

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].original_document_id == document.id
        assert isinstance(pages[0].image, Image.Image)

    def test_load_single_image_converts_to_rgb(
        self, loader: FileSystemDocumentLoader, tmp_path: Path
    ):
        """Test that images are converted to RGB mode."""
        image_path = tmp_path / "test_rgba.png"
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        img.save(image_path)

        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PNG
        )
        document.file_path = str(image_path)

        pages = list(loader.load_pages(document))

        assert pages[0].image.mode == "RGB"

    @pytest.mark.parametrize(
        "expected_page_count,page_numbers",
        [(2, [1, 2])],
    )
    def test_load_pdf_pages(
        self,
        loader: FileSystemDocumentLoader,
        pdf_file: Path,
        tmp_path: Path,
        expected_page_count: int,
        page_numbers: list[int],
    ):
        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PDF
        )
        document.file_path = str(pdf_file)

        pages = list(loader.load_pages(document))

        assert len(pages) == expected_page_count
        assert [page.page_number for page in pages] == page_numbers
        assert all(isinstance(page.image, Image.Image) for page in pages)
        assert all(page.image.mode == "RGB" for page in pages)
        assert all(page.original_document_id == document.id for page in pages)

    def test_load_pages_is_lazy_for_pdf(
        self, loader: FileSystemDocumentLoader, pdf_file: Path, tmp_path: Path
    ):
        """Test that PDF loading is lazy (returns iterator)."""
        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PDF
        )
        document.file_path = str(pdf_file)

        pages_iterator = loader.load_pages(document)

        assert hasattr(pages_iterator, "__iter__")
        assert hasattr(pages_iterator, "__next__")

    @pytest.mark.parametrize("file_type", [model.FileType.PNG, model.FileType.JPEG])
    def test_load_different_image_formats(
        self,
        loader: FileSystemDocumentLoader,
        tmp_path: Path,
        file_type: model.FileType,
    ):
        """Test loading different image formats."""
        image_path = tmp_path / f"test{file_type.dot_extension}"
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(image_path)

        document = factories.generate_document(dir_path=tmp_path, file_type=file_type)
        document.file_path = str(image_path)

        pages = list(loader.load_pages(document))

        assert len(pages) == 1
        assert pages[0].image.mode == "RGB"
