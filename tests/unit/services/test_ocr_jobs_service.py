from pathlib import Path

import pytest

from kul_ocr.domain.model import JobStatus, FileType, SimpleOCRValue
from kul_ocr.service_layer import services
from kul_ocr.service_layer.uow import FakeUnitOfWork
from tests import factories


# --- get_ocr_jobs_by_status tests ---


@pytest.mark.parametrize(
    "status,expected_count",
    [
        (JobStatus.PENDING, 3),
        (JobStatus.PROCESSING, 2),
        (JobStatus.COMPLETED, 4),
        (JobStatus.FAILED, 1),
    ],
)
def test_get_ocr_jobs_by_status(
    uow: FakeUnitOfWork, status: JobStatus, expected_count: int
):
    all_jobs = (
        *factories.generate_ocr_jobs(3, status=JobStatus.PENDING),
        *factories.generate_ocr_jobs(2, status=JobStatus.PROCESSING),
        *factories.generate_ocr_jobs(4, status=JobStatus.COMPLETED),
        *factories.generate_ocr_jobs(1, status=JobStatus.FAILED),
    )

    for job in all_jobs:
        uow.jobs.add(job)

    jobs_by_status = services.get_ocr_jobs_by_status(status, uow)
    assert len(jobs_by_status) == expected_count
    assert uow.commited


def test_get_ocr_jobs_by_status_empty_when_no_matches(uow: FakeUnitOfWork):
    all_jobs = (*factories.generate_ocr_jobs(3, status=JobStatus.PENDING),)

    for job in all_jobs:
        uow.jobs.add(job)

    jobs_by_status = services.get_ocr_jobs_by_status(JobStatus.COMPLETED, uow)
    assert len(jobs_by_status) == 0


def test_get_ocr_jobs_by_status_empty_when_no_jobs_available(uow: FakeUnitOfWork):
    jobs = services.get_ocr_jobs_by_status(JobStatus.PENDING, uow)

    assert jobs == []


# --- get_ocr_jobs_by_document_id tests ---


def test_get_ocr_jobs_by_document_id(uow: FakeUnitOfWork):
    """Test retrieving jobs for a specific document."""
    document_id = "doc-123"

    # Create jobs for the target document
    target_jobs = [
        factories.generate_ocr_job(status=JobStatus.PENDING),
        factories.generate_ocr_job(status=JobStatus.COMPLETED),
        factories.generate_ocr_job(status=JobStatus.FAILED),
    ]
    for job in target_jobs:
        job.document_id = document_id
        uow.jobs.add(job)

    # Create jobs for other documents
    other_jobs = factories.generate_ocr_jobs(5)
    for job in other_jobs:
        uow.jobs.add(job)

    # Retrieve jobs for our target document
    jobs = services.get_ocr_jobs_by_document_id(document_id, uow)

    assert len(jobs) == 3
    assert all(job.document_id == document_id for job in jobs)
    assert uow.commited


def test_get_ocr_jobs_by_document_id_empty_when_no_matches(uow: FakeUnitOfWork):
    """Test that empty list is returned when document has no jobs."""
    # Add jobs for other documents
    jobs = factories.generate_ocr_jobs(5)
    for job in jobs:
        uow.jobs.add(job)

    # Query for document that has no jobs
    result = services.get_ocr_jobs_by_document_id("nonexistent-doc", uow)

    assert result == []


# --- get_terminal_ocr_jobs tests ---


def test_get_terminal_ocr_jobs(uow: FakeUnitOfWork):
    """Test retrieving only terminal (completed/failed) jobs."""
    all_jobs = (
        *factories.generate_ocr_jobs(3, status=JobStatus.PENDING),
        *factories.generate_ocr_jobs(2, status=JobStatus.PROCESSING),
        *factories.generate_ocr_jobs(4, status=JobStatus.COMPLETED),
        *factories.generate_ocr_jobs(1, status=JobStatus.FAILED),
    )

    for job in all_jobs:
        uow.jobs.add(job)

    terminal_jobs = services.get_terminal_ocr_jobs(uow)

    # Should get 4 completed + 1 failed = 5 total
    assert len(terminal_jobs) == 5
    assert all(job.is_terminal for job in terminal_jobs)
    assert uow.commited


def test_get_terminal_ocr_jobs_empty_when_none_terminal(uow: FakeUnitOfWork):
    """Test that empty list is returned when no terminal jobs exist."""
    all_jobs = (
        *factories.generate_ocr_jobs(3, status=JobStatus.PENDING),
        *factories.generate_ocr_jobs(2, status=JobStatus.PROCESSING),
    )

    for job in all_jobs:
        uow.jobs.add(job)

    terminal_jobs = services.get_terminal_ocr_jobs(uow)

    assert terminal_jobs == []


# --- submit_ocr_job tests ---


def test_submit_ocr_job_success(uow: FakeUnitOfWork, tmp_path: Path):
    """Test successfully submitting an OCR job for a document."""
    # First create a document
    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)

    # Submit OCR job
    job = services.submit_ocr_job(document.id, uow)

    assert job.document_id == document.id
    assert job.status == JobStatus.PENDING
    assert uow.jobs.get(job.id) is not None
    assert uow.commited


def test_submit_ocr_job_document_not_found(uow: FakeUnitOfWork):
    """Test that submitting a job for non-existent document raises error."""
    with pytest.raises(ValueError, match="Document .* not found"):
        _ = services.submit_ocr_job("nonexistent-doc", uow)


# --- start_ocr_job_processing tests ---


def test_start_ocr_job_processing_success(uow: FakeUnitOfWork):
    """Test successfully starting a pending job."""
    # Create a pending job
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    uow.jobs.add(job)

    # Start processing
    updated_job = services.start_ocr_job_processing(job.id, uow)

    assert updated_job.status == JobStatus.PROCESSING
    assert updated_job.started_at is not None
    assert uow.commited


def test_start_ocr_job_processing_job_not_found(uow: FakeUnitOfWork):
    """Test that starting non-existent job raises error."""
    with pytest.raises(ValueError, match="OCR Job .* not found"):
        _ = services.start_ocr_job_processing("nonexistent-job", uow)


def test_start_ocr_job_processing_already_processing(uow: FakeUnitOfWork):
    """Test that starting an already processing job raises error."""
    # Create a job that's already processing
    job = factories.generate_ocr_job(status=JobStatus.PROCESSING)
    uow.jobs.add(job)

    # Attempting to start it again should fail
    with pytest.raises(RuntimeError, match="has already been processed"):
        _ = services.start_ocr_job_processing(job.id, uow)


# --- retry_failed_job tests ---


def test_retry_failed_job_success(uow: FakeUnitOfWork):
    """Test successfully retrying a failed job."""
    # Create a failed job
    failed_job = factories.generate_ocr_job(status=JobStatus.FAILED)
    failed_job.error_message = "Original error"
    uow.jobs.add(failed_job)

    # Retry the job
    new_job = services.retry_failed_job(failed_job.id, uow)

    assert new_job.id != failed_job.id
    assert new_job.document_id == failed_job.document_id
    assert new_job.status == JobStatus.PENDING
    assert new_job.error_message is None
    assert uow.commited


def test_retry_failed_job_not_found(uow: FakeUnitOfWork):
    """Test that retrying non-existent job raises error."""
    with pytest.raises(ValueError, match="OCR Job .* not found"):
        _ = services.retry_failed_job("nonexistent-job", uow)


@pytest.mark.parametrize(
    "status",
    [
        JobStatus.PENDING,
        JobStatus.PROCESSING,
        JobStatus.COMPLETED,
    ],
)
def test_retry_failed_job_wrong_status(uow: FakeUnitOfWork, status: JobStatus):
    """Test that retrying a non-failed job raises error."""
    job = factories.generate_ocr_job(status=status)
    uow.jobs.add(job)

    with pytest.raises(ValueError, match="only failed jobs can be retried"):
        _ = services.retry_failed_job(job.id, uow)


# --- get_latest_result_for_document tests ---


def test_get_latest_result_for_document_success(uow: FakeUnitOfWork):
    """Test getting the latest result for a document with multiple completed jobs."""
    document_id = "doc-123"

    # Create multiple completed jobs for the same document
    job1 = factories.generate_ocr_job(status=JobStatus.PENDING)
    job1.document_id = document_id
    job1.mark_as_processing()
    job1.complete()
    uow.jobs.add(job1)

    job2 = factories.generate_ocr_job(status=JobStatus.PENDING)
    job2.document_id = document_id
    job2.mark_as_processing()
    job2.complete()
    uow.jobs.add(job2)

    # Create results for both jobs
    result1 = factories.generate_ocr_result(value_type=SimpleOCRValue, job_id=job1.id)
    result2 = factories.generate_ocr_result(value_type=SimpleOCRValue, job_id=job2.id)
    uow.results.add(result1)
    uow.results.add(result2)

    # Get the latest result
    latest_result = services.get_latest_result_for_document(document_id, uow)

    # Should get the result from the most recent job (job2)
    assert latest_result is not None
    assert latest_result.job_id == job2.id
    assert uow.commited


def test_get_latest_result_for_document_no_completed_jobs(uow: FakeUnitOfWork):
    """Test that None is returned when document has no completed jobs."""
    document_id = "doc-123"

    # Create only pending jobs
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.document_id = document_id
    uow.jobs.add(job)

    result = services.get_latest_result_for_document(document_id, uow)

    assert result is None


def test_get_latest_result_for_document_no_jobs(uow: FakeUnitOfWork):
    """Test that None is returned when document has no jobs."""
    result = services.get_latest_result_for_document("nonexistent-doc", uow)

    assert result is None
