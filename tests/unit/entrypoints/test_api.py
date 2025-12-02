from io import BytesIO
from typing import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from kul_ocr.domain import model
from kul_ocr.entrypoints.api import app
from kul_ocr.entrypoints import dependencies
from kul_ocr.domain.model import Document, FileType
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


@pytest.fixture
def stored_document(fake_storage: FakeFileStorage, fake_uow: FakeUnitOfWork):
    document_id = uuid4()
    document_id_str = str(document_id)
    filename = f"{document_id_str}.pdf"
    file_bytes = b"%PDF-1.4 fake streamed content"

    fake_storage.files[filename] = file_bytes

    doc = Document(
        id=document_id_str,
        file_path=filename,
        file_type=FileType.PDF,
        file_size_bytes=len(file_bytes),
    )

    fake_uow.documents.add(doc)

    return document_id_str, filename, file_bytes



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
    assert len(fake_uow.documents.added) == 1
    assert fake_uow.committed is True

@pytest.mark.asyncio
async def test_download_document_success(
    client: AsyncClient,
    override_dependencies,
    stored_document,
):
    document_id, _, expected_content = stored_document

    response = await client.get(f"/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.content == expected_content


@pytest.mark.asyncio
async def test_download_document_content_type(
    client: AsyncClient,
    override_dependencies,
    stored_document,
):
    document_id, _, _ = stored_document

    response = await client.get(f"/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_document_content_disposition(
    client: AsyncClient,
    override_dependencies,
    stored_document,
):
    document_id, _, _ = stored_document
    expected_filename = f"{document_id}.pdf"

    response = await client.get(f"/documents/{document_id}/download")

    cd = response.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert expected_filename in cd


@pytest.mark.asyncio
async def test_download_document_not_found(
    client: AsyncClient,
    override_dependencies,
):
    missing_id = uuid4()

    response = await client.get(f"/documents/{missing_id}/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_download_document_content_correct(
    client: AsyncClient,
    override_dependencies,
    stored_document,
):
    document_id, _, expected_bytes = stored_document

    response = await client.get(f"/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.content == expected_bytes

