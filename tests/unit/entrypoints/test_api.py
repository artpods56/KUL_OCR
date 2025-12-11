from io import BytesIO
from typing import Iterator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from unittest.mock import patch

from kul_ocr.domain import model
from kul_ocr.entrypoints.api import app
from kul_ocr.entrypoints import dependencies
from kul_ocr.domain.model import Document, FileType, JobStatus, OCRJob
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


@pytest.mark.asyncio
async def test_create_ocr_job_returns_pending_job(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    document_id = str(uuid4())
    doc = Document(
        id=document_id,
        file_path="test.pdf",
        file_type=model.FileType.PDF,
        file_size_bytes=123,
    )
    fake_uow.documents.add(doc)
    fake_uow.commit()

    with patch("kul_ocr.entrypoints.tasks.process_ocr_job_task.delay") as mock_delay:
        response = await client.post("/ocr/jobs", json={"document_id": document_id})

        assert response.status_code == 201
        data = response.json()

        assert data["document_id"] == document_id
        assert data["status"] == "pending"
        assert "id" in data

        saved_job = fake_uow.jobs.get(data["id"])
        assert saved_job is not None
        assert saved_job.document_id == document_id

        mock_delay.assert_called_once_with(data["id"])


@pytest.mark.asyncio
async def test_create_ocr_job_returns_404_for_nonexistent_document(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    non_existent_id = str(uuid4())

    response = await client.post("/ocr/jobs", json={"document_id": non_existent_id})

    assert response.status_code == 404
    assert response.json()["message"] == f"Document with ID {non_existent_id} not found"

    assert len(fake_uow.jobs.list_all()) == 0


@pytest.mark.asyncio
async def test_create_ocr_job_returns_409_when_job_already_pending(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    document_id = str(uuid4())
    doc = Document(
        id=document_id,
        file_path="test.pdf",
        file_type=model.FileType.PDF,
        file_size_bytes=123,
    )
    fake_uow.documents.add(doc)

    existing_job = OCRJob(
        id="job-123", document_id=document_id, status=JobStatus.PENDING
    )
    fake_uow.jobs.add(existing_job)
    fake_uow.commit()

    with patch("kul_ocr.entrypoints.tasks.process_ocr_job_task.delay") as mock_delay:
        response = await client.post("/ocr/jobs", json={"document_id": document_id})

    assert response.status_code == 409
    assert "already has a pending" in response.json()["message"]

    mock_delay.assert_not_called()


@pytest.mark.asyncio
async def test_create_ocr_job_validates_request_body(
    client: AsyncClient,
    override_dependencies: None,
) -> None:
    response = await client.post("/ocr/jobs", json={})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"
