from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from kul_ocr.domain import model
from kul_ocr.domain.model import Document, FileType, JobStatus, Job
from kul_ocr.entrypoints import dependencies, schemas
from kul_ocr.entrypoints.api import app
from tests import factories
from tests.factories import generate_document, generate_ocr_job, generate_ocr_result
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


@pytest.fixture
def stored_document(
    fake_storage: FakeFileStorage, fake_uow: FakeUnitOfWork
) -> tuple[str, str, bytes]:
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
    file_content: bytes = b"fake pdf content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

    response = await client.post("/documents", files=files)

    document = schemas.DocumentResponse(**response.json())

    assert response.status_code == 200

    assert document.file_type == model.FileType.PDF.value

    assert document.file_size_bytes == len(file_content)

    assert fake_storage.save_call_count == 1
    fake_uow_docs = cast(FakeDocumentRepository, fake_uow.documents)
    assert len(fake_uow_docs.added) == 1
    assert fake_uow.committed is True


@pytest.mark.asyncio
async def test_get_document_success(
    client: AsyncClient, fake_uow: FakeUnitOfWork, override_dependencies: None
) -> None:
    """Document exists and returned correctly."""
    doc = generate_document(dir_path=Path("fake_dir"), file_size_in_bytes=1234)
    fake_uow.documents.add(doc)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc.id}")

    assert response.status_code == 200
    parsed_response = schemas.DocumentResponse(**response.json())
    assert str(parsed_response.id) == doc.id
    assert parsed_response.file_path == doc.file_path


@pytest.mark.asyncio
async def test_get_document_not_found(
    client: AsyncClient, override_dependencies: None
) -> None:
    """Should return 404 when document does not exist."""

    response = await client.get("/documents/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_get_latest_result_success(
    client: AsyncClient, fake_uow: FakeUnitOfWork, override_dependencies: None
) -> None:
    """Document exists and has OCR result attached."""
    doc = generate_document(dir_path=Path("fake_dir"), file_size_in_bytes=1234)
    ocr_job = generate_ocr_job()
    ocr_job.status = model.JobStatus.COMPLETED
    ocr_job.document_id = doc.id
    ocr_result = generate_ocr_result()
    ocr_result.job_id = ocr_job.id

    fake_uow.documents.add(doc)
    fake_uow.jobs.add(ocr_job)
    fake_uow.results.add(ocr_result)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc.id}/latest-result")

    assert response.status_code == 200
    parsed_response = schemas.OcrResultResponse(**response.json())
    assert str(parsed_response.id) == ocr_result.id


@pytest.mark.asyncio
async def test_get_latest_result_no_result(
    client: AsyncClient, fake_uow: FakeUnitOfWork, override_dependencies: None
) -> None:
    """Document exists but has no completed OCR result."""
    doc = generate_document(dir_path=Path("fake_dir"), file_size_in_bytes=1234)
    fake_uow.documents.add(doc)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc.id}/latest-result")

    assert response.status_code == 404
    assert "No OCR result found" in response.json()["detail"]


@pytest.fixture(autouse=True)
def setup_override(fake_uow: FakeUnitOfWork) -> Iterator[None]:
    app.dependency_overrides[dependencies.get_uow] = lambda: fake_uow
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_ocr_jobs_returns_all_jobs(
    client: AsyncClient, fake_uow: FakeUnitOfWork
) -> None:
    doc = factories.generate_document(dir_path=Path("/tmp"))
    fake_uow.documents.add(doc)

    job1 = factories.generate_ocr_job(status=model.JobStatus.PENDING)
    job1.document_id = doc.id

    job2 = factories.generate_ocr_job(status=model.JobStatus.COMPLETED)
    job2.document_id = doc.id

    fake_uow.jobs.add(job1)
    fake_uow.jobs.add(job2)
    fake_uow.commit()

    response = await client.get("/ocr/jobs")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    assert data["total"] == 2
    assert len(data["jobs"]) == 2

    ids: list[str] = [job["id"] for job in data["jobs"]]
    assert job1.id in ids
    assert job2.id in ids


@pytest.mark.asyncio
async def test_list_ocr_jobs_filters_by_status(
    client: AsyncClient, fake_uow: FakeUnitOfWork
) -> None:
    doc = factories.generate_document(dir_path=Path("/tmp"))
    fake_uow.documents.add(doc)

    target_job = factories.generate_ocr_job(status=model.JobStatus.COMPLETED)
    target_job.document_id = doc.id

    other_job = factories.generate_ocr_job(status=model.JobStatus.PENDING)
    other_job.document_id = doc.id

    fake_uow.jobs.add(target_job)
    fake_uow.jobs.add(other_job)
    fake_uow.commit()

    response = await client.get(f"/ocr/jobs?status={model.JobStatus.COMPLETED.value}")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    assert data["total"] == 1
    assert data["jobs"][0]["id"] == target_job.id
    assert data["jobs"][0]["status"] == model.JobStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_list_ocr_jobs_filters_by_document_id(
    client: AsyncClient, fake_uow: FakeUnitOfWork
) -> None:
    doc_target = factories.generate_document(dir_path=Path("/tmp"))
    doc_other = factories.generate_document(dir_path=Path("/tmp"))
    fake_uow.documents.add(doc_target)
    fake_uow.documents.add(doc_other)

    job1 = factories.generate_ocr_job(status=model.JobStatus.PENDING)
    job1.document_id = doc_target.id

    job2 = factories.generate_ocr_job(status=model.JobStatus.COMPLETED)
    job2.document_id = doc_target.id

    job_other = factories.generate_ocr_job(status=model.JobStatus.PENDING)
    job_other.document_id = doc_other.id

    fake_uow.jobs.add(job1)
    fake_uow.jobs.add(job2)
    fake_uow.jobs.add(job_other)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc_target.id}")  # Verify doc exists
    assert response.status_code == 200

    response = await client.get(f"/ocr/jobs?document_id={doc_target.id}")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    assert data["total"] == 2
    returned_ids: set[str] = {job["id"] for job in data["jobs"]}
    assert returned_ids == {job1.id, job2.id}
    assert job_other.id not in returned_ids


@pytest.mark.asyncio
async def test_list_ocr_jobs_filters_by_both(
    client: AsyncClient, fake_uow: FakeUnitOfWork
) -> None:
    doc_a = factories.generate_document(dir_path=Path("/tmp"))
    doc_b = factories.generate_document(dir_path=Path("/tmp"))
    fake_uow.documents.add(doc_a)
    fake_uow.documents.add(doc_b)

    target_job = factories.generate_ocr_job(status=model.JobStatus.COMPLETED)
    target_job.document_id = doc_a.id

    wrong_status = factories.generate_ocr_job(status=model.JobStatus.PENDING)
    wrong_status.document_id = doc_a.id

    wrong_doc = factories.generate_ocr_job(status=model.JobStatus.COMPLETED)
    wrong_doc.document_id = doc_b.id

    fake_uow.jobs.add(target_job)
    fake_uow.jobs.add(wrong_status)
    fake_uow.jobs.add(wrong_doc)
    fake_uow.commit()

    url = f"/ocr/jobs?document_id={doc_a.id}&status={model.JobStatus.COMPLETED.value}"
    response = await client.get(url)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    assert data["total"] == 1
    assert data["jobs"][0]["id"] == target_job.id


@pytest.mark.asyncio
async def test_list_ocr_jobs_returns_empty_when_no_matches(
    client: AsyncClient, fake_uow: FakeUnitOfWork
) -> None:
    job = factories.generate_ocr_job(status=model.JobStatus.PENDING)
    fake_uow.jobs.add(job)
    fake_uow.commit()

    response = await client.get(f"/ocr/jobs?status={model.JobStatus.FAILED.value}")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["total"] == 0
    assert data["jobs"] == []


@pytest.mark.asyncio
async def test_list_ocr_jobs_returns_400_for_invalid_status(
    client: AsyncClient, fake_uow: FakeUnitOfWork
) -> None:
    invalid_status = "super_invalid_status"
    response = await client.get(f"/ocr/jobs?status={invalid_status}")

    assert response.status_code == 400
    data: dict[str, Any] = response.json()

    assert "message" in data
    error_msg: str = data["message"]
    assert invalid_status in error_msg


@pytest.mark.asyncio
async def test_create_ocr_job_returns_pending_job(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    document_id: str = str(uuid4())
    doc = Document(
        id=document_id,
        file_path="test.pdf",
        file_type=model.FileType.PDF,
        file_size_bytes=123,
    )
    fake_uow.documents.add(doc)
    fake_uow.commit()

    response = await client.post("/ocr/jobs", json={"document_id": document_id})

    assert response.status_code == 201
    data: dict[str, Any] = response.json()

    assert data["document_id"] == document_id
    assert data["status"] == "pending"
    assert "id" in data

    saved_job = fake_uow.jobs.get(data["id"])
    assert saved_job is not None
    assert saved_job.document_id == document_id


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Celery tasks require RabbitMQ broker which is not available in test environment"
)
async def test_start_ocr_job_success(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    """Test starting an OCR job triggers the Celery task."""
    document_id = str(uuid4())
    job_id = str(uuid4())

    doc = Document(
        id=document_id,
        file_path="test.pdf",
        file_type=model.FileType.PDF,
        file_size_bytes=123,
    )
    job = Job(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    fake_uow.documents.add(doc)
    fake_uow.jobs.add(job)
    fake_uow.commit()

    with patch("kul_ocr.entrypoints.tasks.process_ocr_job_task.delay") as mock_delay:
        response = await client.post(f"/ocr/jobs/{job_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["id"] == job_id

        # Verify job status in DB
        saved_job = fake_uow.jobs.get(job_id)
        assert saved_job is not None
        assert saved_job.status == JobStatus.PROCESSING

        # Verify Celery task was triggered
        mock_delay.assert_called_once_with(job_id)


@pytest.mark.asyncio
async def test_create_ocr_job_returns_404_for_nonexistent_document(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    non_existent_id: str = str(uuid4())

    response = await client.post("/ocr/jobs", json={"document_id": non_existent_id})

    assert response.status_code == 404
    assert response.json()["message"] == f"Document with ID {non_existent_id} not found"

    assert len(fake_uow.jobs.list_all()) == 0


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Celery tasks require RabbitMQ broker which is not available in test environment"
)
async def test_create_ocr_job_returns_409_when_job_already_pending(
    client: AsyncClient,
    fake_uow: FakeUnitOfWork,
    override_dependencies: None,
) -> None:
    document_id: str = str(uuid4())
    doc = Document(
        id=document_id,
        file_path="test.pdf",
        file_type=model.FileType.PDF,
        file_size_bytes=123,
    )
    fake_uow.documents.add(doc)

    existing_job = Job(id="job-123", document_id=document_id, status=JobStatus.PENDING)
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
