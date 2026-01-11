import io
from pathlib import Path

import pytest

from kul_ocr.adapters.storages.local import LocalFileStorage
from kul_ocr.domain.model import FileType, JobStatus, SimpleOCRValue
from kul_ocr.service_layer import services
from tests.fakes.uow import FakeUnitOfWork
from tests import factories


# --- upload_document tests ---


@pytest.mark.parametrize(
    "file_type", [FileType.JPEG, FileType.PNG, FileType.PDF, FileType.WEBP]
)
def test_upload_document(uow: FakeUnitOfWork, tmp_path: Path, file_type: FileType):
    storage = LocalFileStorage(storage_root=tmp_path)

    file_content = b"test content"
    file_stream = io.BytesIO(file_content)

    document = services.upload_document(
        file_stream=file_stream,
        file_size=0,
        file_type=file_type,
        storage=storage,
        uow=uow,
    )
    
    assert uow.documents.get(document_id=document.id) is not None
    assert document.file_type == file_type.value
    assert uow.committed


def test_upload_document_auto_generates_id(uow: FakeUnitOfWork, tmp_path: Path):
    """Test that document ID is auto-generated."""
    storage = LocalFileStorage(storage_root=tmp_path)
    file_stream = io.BytesIO(b"test content")

    document = services.upload_document(
        file_stream=file_stream,
        file_size=0,
        file_type=FileType.PDF,
        storage=storage,
        uow=uow,
    )

    assert document.id is not None
    assert len(document.id) > 0


# --- get_document_with_latest_result tests ---


def test_get_document_with_latest_result_success(uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting document with its latest OCR result."""
    # Create a document
    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)

    # Create multiple completed jobs for this document
    job1 = factories.generate_ocr_job(status=JobStatus.PENDING)
    job1.document_id = document.id
    job1.mark_as_processing()
    job1.complete()
    uow.jobs.add(job1)

    job2 = factories.generate_ocr_job(status=JobStatus.PENDING)
    job2.document_id = document.id
    job2.mark_as_processing()
    job2.complete()
    uow.jobs.add(job2)

    # Create results for both jobs
    result1 = factories.generate_ocr_result(value_type=SimpleOCRValue, job_id=job1.id)
    result2 = factories.generate_ocr_result(value_type=SimpleOCRValue, job_id=job2.id)
    uow.results.add(result1)
    uow.results.add(result2)

    # Get document with latest result
    doc, result = services.get_document_with_latest_result(document.id, uow)

    assert doc.id == document.id
    assert result is not None
    assert result.job_id == job2.id
    assert isinstance(result.content, SimpleOCRValue)
    assert uow.committed


def test_get_document_with_latest_result_no_results(
    uow: FakeUnitOfWork, tmp_path: Path
):
    """Test getting document when it has no completed jobs."""
    # Create a document
    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)

    # Create only a pending job (not completed)
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.document_id = document.id
    uow.jobs.add(job)

    # Get document with latest result
    doc, result = services.get_document_with_latest_result(document.id, uow)

    assert doc.id == document.id
    assert result is None


def test_get_document_with_latest_result_document_not_found(uow: FakeUnitOfWork):
    """Test that getting non-existent document raises error."""
    with pytest.raises(ValueError, match="Document .* not found"):
        services.get_document_with_latest_result("nonexistent-doc", uow)


def test_get_document_with_latest_result_no_jobs(uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting document when it has no jobs at all."""
    # Create a document
    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)

    # Get document with latest result
    doc, result = services.get_document_with_latest_result(document.id, uow)

    assert doc.id == document.id
    assert result is None
