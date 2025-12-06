from io import BytesIO
from typing import Iterator, cast
from pathlib import Path

import pytest
from httpx import AsyncClient

from kul_ocr.domain import model
from kul_ocr.domain.model import SimpleOCRValue
from kul_ocr.entrypoints.api import app
from kul_ocr.entrypoints import dependencies, schemas
from tests.fakes.repositories import FakeDocumentRepository
from tests.fakes.storages import FakeFileStorage
from tests.fakes.uow import FakeUnitOfWork
from tests.factories import generate_document, generate_ocr_job, generate_ocr_result


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

    document = schemas.DocumentResponse(**response.json())

    assert response.status_code == 200

    assert document.file_type.value == model.FileType.PDF.value
    assert document.file_size_bytes == len(file_content)

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
    doc = generate_document(dir_path=Path("fake_dir"), file_size_in_bytes=1234)

    ocr_job = generate_ocr_job()

    ocr_job.status = model.JobStatus.COMPLETED

    # [TODO] check why is the method not marking the job as completed
    # ocr_job.complete()

    ocr_job.document_id = doc.id

    ocr_result = generate_ocr_result(value_type=SimpleOCRValue)
    ocr_result.job_id = ocr_job.id

    fake_uow.documents.add(doc)
    fake_uow.jobs.add(ocr_job)
    fake_uow.results.add(ocr_result)

    response = await client.get(f"/documents/{doc.id}")

    print(response.json())

    assert response.status_code == 200

    parsed_document = schemas.DocumentWithResultResponses(**response.json())

    # Debug: print what you're actually getting
    print(f"latest_result: {parsed_document.latest_result}")
    print(f"ocr_result: {ocr_result}")

    # Compare specific fields instead of whole objects
    assert parsed_document.latest_result is not None
    assert parsed_document.latest_result.id == ocr_result.id
    assert parsed_document.latest_result.job_id == ocr_result.job_id
    # data = response.json()
    #
    # ocr_data = data.get("ocr_result")
    # assert ocr_data is not None
    # assert ocr_data["id"] == ocr_result.id
    # assert ocr_data["text"] == ocr_result.content


@pytest.mark.asyncio
async def test_get_document_without_ocr(
    client: AsyncClient, fake_uow: FakeUnitOfWork, override_dependencies
):
    """Document exists but has no OCR result."""
    doc = generate_document(dir_path=Path("fake_dir"), file_size_in_bytes=1234)
    fake_uow.documents.add(doc)
    fake_uow.commit()

    response = await client.get(f"/documents/{doc.id}")

    assert response.status_code == 200

    parsed_document = schemas.DocumentWithResultResponses(**response.json())

    assert parsed_document.latest_result is None
