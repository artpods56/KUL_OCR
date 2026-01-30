from pathlib import Path

import pytest

import core.adapters.database.repository
from backend.documents import service
from core.config import StorageSettings
from core.domain import exceptions
from core.domain.enums import JobStatus, FileType
from tests import factories
from tests.fakes.uow import FakeUnitOfWork
from tests.fakes.storages import FakeFileStorage


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def fake_storage_config(tmp_path: Path) -> StorageSettings:
    return StorageSettings(
        storage_type="local",
        storage_root=tmp_path,
        staging_prefix="staging",
        documents_prefix="documents",
    )


def test_get_document_returns_existing_document(
    fake_uow: FakeUnitOfWork, tmp_path: Path
):
    """Test getting an existing document."""
    document = factories.generate_document(dir_path=tmp_path)
    fake_uow.documents.add(document)

    retrieved = fake_uow.documents.get(document.id)

    assert retrieved is not None
    assert retrieved.id == document.id


def test_get_document_not_found(fake_uow: FakeUnitOfWork):
    """Test that getting non-existent document returns None."""
    result = fake_uow.documents.get("nonexistent-doc")

    assert result is None


def test_upload_document(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test uploading a document."""
    from io import BytesIO

    fake_storage = FakeFileStorage()

    # Prepare the document
    document = service.prepare_document(
        file_name="test.pdf",
        file_type=FileType.PDF,
        file_size=26,
    )

    staging_path = Path("staging") / f"{document.id}.pdf"
    uploaded_path = Path("documents") / f"{document.id}.pdf"

    result = service.upload_document(
        file_stream=BytesIO(b"%PDF-1.4 fake file content"),
        document=document,
        staging_file_path=staging_path,
        uploaded_file_path=uploaded_path,
        storage=fake_storage,
        uow=fake_uow,
    )

    assert result.id is not None
    assert result.file_type == FileType.PDF.value
    assert result.original_filename == "test.pdf"


def test_upload_document_extension_mismatch(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test that document with mismatched extension raises FileExtensionMismatchError."""
    from io import BytesIO

    file_stream = BytesIO(b"%PDF-1.4 fake pdf content")
    file_name = "test.txt"  # .txt extension but PDF file_type

    with pytest.raises(
        exceptions.FileExtensionMismatchError, match="File extension mismatch"
    ):
        _ = service.validate_uploaded_file(
            file_stream=file_stream,
            file_size=24,
            file_type=FileType.PDF,
            max_bytes=50 * 1024 * 1024,
            file_name=file_name,
        )


def test_get_document_for_processing(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting document for OCR processing."""
    document = factories.generate_document(dir_path=tmp_path)
    fake_uow.documents.add(document)

    result = service.get_document_for_processing(document.id, fake_uow)

    assert result.id == document.id
    assert result.file_path == document.file_path


def test_get_document_for_processing_not_found(fake_uow: FakeUnitOfWork):
    """Test getting non-existent document raises exception."""
    with pytest.raises(
        core.adapters.database.repository.DocumentNotFoundError,
        match="Document not found",
    ):
        service.get_document_for_processing("nonexistent-doc", fake_uow)


def test_get_latest_result_for_document(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting latest result for a document."""
    document = factories.generate_document(tmp_path)
    job = factories.generate_ocr_job()
    job.status = JobStatus.COMPLETED
    job.document_id = document.id
    ocr_result = factories.generate_ocr_result()
    ocr_result.job_id = job.id

    fake_uow.documents.add(document)
    fake_uow.jobs.add(job)
    fake_uow.results.add(ocr_result)

    result = service.get_latest_result_for_document(document.id, fake_uow)

    assert result is not None
    assert str(result.id) == str(ocr_result.id)


def test_get_latest_result_for_document_not_found(
    fake_uow: FakeUnitOfWork, tmp_path: Path
):
    """Test that getting result for non-existent document raises exception."""
    with pytest.raises(
        core.adapters.database.repository.DocumentNotFoundError,
        match="Document not found",
    ):
        service.get_latest_result_for_document("nonexistent-doc", fake_uow)


def test_get_latest_result_for_document_no_results(
    fake_uow: FakeUnitOfWork, tmp_path: Path
):
    """Test that getting result for document with no completed jobs returns None."""
    document = factories.generate_document(tmp_path)
    fake_uow.documents.add(document)

    result = service.get_latest_result_for_document(document.id, fake_uow)

    assert result is None


def test_get_document_with_latest_result(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting document with its latest result."""
    document = factories.generate_document(tmp_path)
    job = factories.generate_ocr_job()
    job.status = JobStatus.COMPLETED
    job.document_id = document.id
    ocr_result = factories.generate_ocr_result()
    ocr_result.job_id = job.id

    fake_uow.documents.add(document)
    fake_uow.jobs.add(job)
    fake_uow.results.add(ocr_result)

    doc, result = service.get_document_with_latest_result(document.id, fake_uow)

    assert doc.id == document.id
    assert result is not None
    assert result.job_id == job.id


def test_get_document_with_latest_result_no_results(
    fake_uow: FakeUnitOfWork, tmp_path: Path
):
    """Test getting document when it has no completed jobs."""
    document = factories.generate_document(tmp_path)
    fake_uow.documents.add(document)

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.document_id = document.id
    fake_uow.jobs.add(job)

    doc, result = service.get_document_with_latest_result(document.id, fake_uow)

    assert doc.id == document.id
    assert result is None


def test_get_document_with_latest_result_document_not_found(fake_uow: FakeUnitOfWork):
    """Test that getting non-existent document raises DocumentNotFoundError."""
    with pytest.raises(
        core.adapters.database.repository.DocumentNotFoundError,
        match="Document not found",
    ):
        service.get_document_with_latest_result("nonexistent-doc", fake_uow)
