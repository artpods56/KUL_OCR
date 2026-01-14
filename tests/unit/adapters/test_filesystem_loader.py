import io
from pathlib import Path

import pytest
from PIL import Image

from kul_ocr.adapters.loaders.filesystem import FileSystemDocumentLoader
from kul_ocr.domain import model, structs
from tests.fakes.storages import FakeFileStorage


@pytest.fixture
def fake_storage() -> FakeFileStorage:
    return FakeFileStorage()


@pytest.fixture
def loader(fake_storage: FakeFileStorage) -> FileSystemDocumentLoader:
    return FileSystemDocumentLoader(storage=fake_storage)


@pytest.fixture
def image_bytes() -> bytes:
    """Create a simple test image as bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def pdf_bytes() -> bytes:
    """Create a simple test PDF with 2 pages as bytes."""
    import pymupdf

    doc = pymupdf.open()

    for _ in range(2):
        page = doc.new_page(width=595, height=842)  # pyright: ignore[reportAttributeAccessIssue]
        page.insert_text((100, 100), "Test content")

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


class TestFileSystemDocumentLoader:
    def test_load_single_image_returns_one_page(
        self,
        loader: FileSystemDocumentLoader,
        fake_storage: FakeFileStorage,
        image_bytes: bytes,
    ):
        fake_storage.save(
            stream=io.BytesIO(image_bytes), file_path=Path("test_image.png")
        )

        doc_input = structs.DocumentInput(
            id="doc-1", file_path="test_image.png", file_type=model.FileType.PNG
        )

        pages = list(loader.load_pages(doc_input))

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].original_document_id == "doc-1"
        assert isinstance(pages[0].image, Image.Image)

    def test_load_single_image_converts_to_rgb(
        self, loader: FileSystemDocumentLoader, fake_storage: FakeFileStorage
    ):
        """Test that images are converted to RGB mode."""
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        fake_storage.save(
            stream=io.BytesIO(image_bytes), file_path=Path("test_rgba.png")
        )

        doc_input = structs.DocumentInput(
            id="doc-2", file_path="test_rgba.png", file_type=model.FileType.PNG
        )

        pages = list(loader.load_pages(doc_input))

        assert pages[0].image.mode == "RGB"

    def test_load_pdf_pages(
        self,
        loader: FileSystemDocumentLoader,
        fake_storage: FakeFileStorage,
        pdf_bytes: bytes,
    ):
        """Test loading PDF with 2 pages."""
        fake_storage.save(stream=io.BytesIO(pdf_bytes), file_path=Path("test.pdf"))

        doc_input = structs.DocumentInput(
            id="doc-3", file_path="test.pdf", file_type=model.FileType.PDF
        )

        pages = list(loader.load_pages(doc_input))

        assert len(pages) == 2
        assert [page.page_number for page in pages] == [1, 2]
        assert all(isinstance(page.image, Image.Image) for page in pages)
        assert all(page.image.mode == "RGB" for page in pages)
        assert all(page.original_document_id == "doc-3" for page in pages)

    def test_load_pages_is_lazy_for_pdf(
        self,
        loader: FileSystemDocumentLoader,
        fake_storage: FakeFileStorage,
        pdf_bytes: bytes,
    ):
        """Test that PDF loading is lazy (returns iterator)."""
        fake_storage.save(stream=io.BytesIO(pdf_bytes), file_path=Path("test.pdf"))

        doc_input = structs.DocumentInput(
            id="doc-4", file_path="test.pdf", file_type=model.FileType.PDF
        )

        pages_iterator = loader.load_pages(doc_input)

        assert hasattr(pages_iterator, "__iter__")
        assert hasattr(pages_iterator, "__next__")

    @pytest.mark.parametrize(
        "file_type,format", [(model.FileType.PNG, "PNG"), (model.FileType.JPEG, "JPEG")]
    )
    def test_load_different_image_formats(
        self,
        loader: FileSystemDocumentLoader,
        fake_storage: FakeFileStorage,
        file_type: model.FileType,
        format: str,
    ):
        """Test loading different image formats."""
        img = Image.new("RGB", (50, 50), color="blue")
        buf = io.BytesIO()
        img.save(buf, format=format)
        image_bytes = buf.getvalue()

        file_path = Path(f"test{file_type.dot_extension}")
        fake_storage.save(stream=io.BytesIO(image_bytes), file_path=file_path)

        doc_input = structs.DocumentInput(
            id="doc-5", file_path=str(file_path), file_type=file_type
        )

        pages = list(loader.load_pages(doc_input))

        assert len(pages) == 1
        assert pages[0].image.mode == "RGB"
