from io import BytesIO
from typing import Iterator, cast

import pytest
from httpx import AsyncClient

from kul_ocr.domain import model
from kul_ocr.entrypoints.api import app
from kul_ocr.entrypoints import dependencies
from tests.fakes.repositories import FakeDocumentRepository
from tests.fakes.storages import FakeFileStorage
from tests.fakes.uow import FakeUnitOfWork


@pytest.fixture
def fake_storage() -> FakeFileStorage:
    return FakeFileStorage()


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def override_dependencies(
    fake_storage: FakeFileStorage,
    fake_uow: FakeUnitOfWork,
) -> Iterator[None]:
    app.dependency_overrides[dependencies.get_file_storage] = lambda: fake_storage
    app.dependency_overrides[dependencies.get_uow] = lambda: fake_uow
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_document_success(
    client: AsyncClient,
    fake_storage: FakeFileStorage,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    """Test successful document upload via POST /documents endpoint."""
    file_content = b"fake pdf content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

    response = await client.post("/documents", files=files)

    assert response.status_code == 200
    data: dict[str, object] = response.json()

    assert data["file_type"] == model.FileType.PDF.value
    assert data["file_size_bytes"] == len(file_content)
    assert all(key in data for key in ["id", "file_path", "uploaded_at"])

    assert fake_storage.save_call_count == 1
    fake_uow_docs = cast(
        FakeDocumentRepository, fake_uow.documents
    )  # to satisfy type checker
    assert len(fake_uow_docs.added) == 1
    assert fake_uow.committed is True


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, override_dependencies):
    """Should return 404 when document does not exist."""
    response = await client.get("/documents/999999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_document_with_ocr(
    client: AsyncClient, fake_uow: FakeUnitOfWork, override_dependencies
):
    """Document exists and has OCR result attached."""
    repo: FakeDocumentRepository = fake_uow.documents  # type: ignore
    doc = repo.create_dummy_document(with_ocr=True)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc.id}")

    assert response.status_code == 200
    data = response.json()

    assert data["ocr_result"]["text"] == doc.ocr_result.text
    assert data["ocr_result"]["id"] == doc.ocr_result.id


@pytest.mark.asyncio
async def test_get_document_without_ocr(
    client: AsyncClient, fake_uow: FakeUnitOfWork, override_dependencies
):
    """Document exists but has no OCR result."""
    repo: FakeDocumentRepository = fake_uow.documents  # type: ignore
    doc = repo.create_dummy_document(with_ocr=False)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc.id}")

    assert response.status_code == 200
    data = response.json()

    assert data["ocr_result"] is None
