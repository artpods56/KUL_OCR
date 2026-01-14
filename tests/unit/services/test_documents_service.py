from pathlib import Path

import pytest

from kul_ocr.domain import exceptions
from kul_ocr.domain.model import FileType, JobStatus
from kul_ocr.service_layer import services
from tests import factories
from tests.fakes.uow import FakeUnitOfWork
from tests.fakes.storages import FakeFileStorage


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


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

    file_stream = BytesIO(b"fake file content")
    fake_storage = FakeFileStorage()

    result = services.upload_document(
        file_stream=file_stream,
        file_size=18,
        file_type=FileType.PDF,
        storage=fake_storage,
        uow=fake_uow,
    )

    assert result.id is not None
    assert result.file_type == FileType.PDF.value


def test_upload_document_extension_mismatch(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test that document with mismatched extension raises ValueError."""
    from io import BytesIO

    file_stream = BytesIO(b"fake txt content")
    file_stream.name = "test.txt"
    fake_storage = FakeFileStorage()

    with pytest.raises(ValueError, match="Document extension mismatch"):
        services.upload_document(
            file_stream=file_stream,
            file_size=16,
            file_type=FileType.PDF,
            storage=fake_storage,
            uow=fake_uow,
        )


def test_get_document_for_processing(fake_uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting document for OCR processing."""
    document = factories.generate_document(dir_path=tmp_path)
    fake_uow.documents.add(document)

    result = services.get_document_for_processing(document.id, fake_uow)

    assert result.id == document.id
    assert result.file_path == document.file_path


def test_get_document_for_processing_not_found(fake_uow: FakeUnitOfWork):
    """Test getting non-existent document raises exception."""
    with pytest.raises(exceptions.DocumentNotFoundError, match="Document .* not found"):
        services.get_document_for_processing("nonexistent-doc", fake_uow)


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

    result = services.get_latest_result_for_document(document.id, fake_uow)

    assert result is not None
    assert str(result.id) == str(ocr_result.id)


def test_get_latest_result_for_document_not_found(
    fake_uow: FakeUnitOfWork, tmp_path: Path
):
    """Test that getting result for non-existent document raises exception."""
    with pytest.raises(exceptions.DocumentNotFoundError, match="Document .* not found"):
        services.get_latest_result_for_document("nonexistent-doc", fake_uow)


def test_get_latest_result_for_document_no_results(
    fake_uow: FakeUnitOfWork, tmp_path: Path
):
    """Test that getting result for document with no completed jobs returns None."""
    document = factories.generate_document(tmp_path)
    fake_uow.documents.add(document)

    result = services.get_latest_result_for_document(document.id, fake_uow)

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

    doc, result = services.get_document_with_latest_result(document.id, fake_uow)

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

    doc, result = services.get_document_with_latest_result(document.id, fake_uow)

    assert doc.id == document.id
    assert result is None


def test_get_document_with_latest_result_document_not_found(fake_uow: FakeUnitOfWork):
    """Test that getting non-existent document raises DocumentNotFoundError."""
    with pytest.raises(exceptions.DocumentNotFoundError, match="Document .* not found"):
        services.get_document_with_latest_result("nonexistent-doc", fake_uow)
