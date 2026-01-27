import uuid
from pathlib import Path

import pytest
from datetime import datetime, timedelta, timezone

import kul_ocr.adapters.database.repository
import kul_ocr.domain.model
import kul_ocr.service_layer.services.jobs
import kul_ocr.service_layer.services.results
from kul_ocr.domain import exceptions
from kul_ocr.domain.enums import JobStatus, FileType
from tests.fakes.uow import FakeUnitOfWork
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

    jobs_by_status = kul_ocr.service_layer.services.jobs.get_ocr_jobs_by_status(
        status, uow
    )
    assert len(jobs_by_status) == expected_count
    # Service no longer commits - that's the caller's responsibility


def test_get_ocr_jobs_by_status_empty_when_no_matches(uow: FakeUnitOfWork):
    all_jobs = (*factories.generate_ocr_jobs(3, status=JobStatus.PENDING),)

    for job in all_jobs:
        uow.jobs.add(job)

    jobs_by_status = kul_ocr.service_layer.services.jobs.get_ocr_jobs_by_status(
        JobStatus.COMPLETED, uow
    )
    assert len(jobs_by_status) == 0


def test_get_ocr_jobs_by_status_empty_when_no_jobs_available(uow: FakeUnitOfWork):
    jobs = kul_ocr.service_layer.services.jobs.get_ocr_jobs_by_status(
        JobStatus.PENDING, uow
    )

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
    jobs = kul_ocr.service_layer.services.jobs.get_ocr_jobs_by_document_id(
        document_id, uow
    )

    assert len(jobs) == 3
    assert all(str(job.document_id) == document_id for job in jobs)
    # Service no longer commits - that's the caller's responsibility


def test_get_ocr_jobs_by_document_id_empty_when_no_matches(uow: FakeUnitOfWork):
    """Test that empty list is returned when document has no jobs."""
    # Add jobs for other documents
    jobs = factories.generate_ocr_jobs(5)
    for job in jobs:
        uow.jobs.add(job)

    # Query for document that has no jobs
    result = kul_ocr.service_layer.services.jobs.get_ocr_jobs_by_document_id(
        "nonexistent-doc", uow
    )

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

    terminal_jobs = kul_ocr.service_layer.services.jobs.get_terminal_ocr_jobs(uow)

    # Should get 4 completed + 1 failed = 5 total
    assert len(terminal_jobs) == 5
    assert all(job.status in ["completed", "failed"] for job in terminal_jobs)
    # Service no longer commits - that's the caller's responsibility


def test_get_terminal_ocr_jobs_empty_when_none_terminal(uow: FakeUnitOfWork):
    """Test that empty list is returned when no terminal jobs exist."""
    all_jobs = (
        *factories.generate_ocr_jobs(3, status=JobStatus.PENDING),
        *factories.generate_ocr_jobs(2, status=JobStatus.PROCESSING),
    )

    for job in all_jobs:
        uow.jobs.add(job)

    terminal_jobs = kul_ocr.service_layer.services.jobs.get_terminal_ocr_jobs(uow)

    assert terminal_jobs == []


# --- submit_ocr_job tests ---


def test_submit_ocr_job_success(uow: FakeUnitOfWork, tmp_path: Path):
    """Test successfully submitting an OCR job for a document."""

    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)

    job = kul_ocr.service_layer.services.jobs.submit_ocr_job(document.id, uow)

    assert str(job.document_id) == document.id
    assert job.status == "pending"

    saved_job = uow.jobs.get(str(job.id))
    assert saved_job is not None
    assert saved_job.status == JobStatus.PENDING
    # Service no longer commits - that's the caller's responsibility


def test_submit_ocr_job_document_not_found(uow: FakeUnitOfWork):
    """Test that submitting a job for non-existent document raises error."""
    with pytest.raises(
        kul_ocr.adapters.database.repository.DocumentNotFoundError,
        match="Document not found",
    ):
        _ = kul_ocr.service_layer.services.jobs.submit_ocr_job("nonexistent-doc", uow)


# --- start_ocr_job_processing tests ---


def test_start_ocr_job_processing_success(uow: FakeUnitOfWork):
    """Test successfully starting a pending job."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    uow.jobs.add(job)

    updated_job = kul_ocr.service_layer.services.jobs.start_ocr_job_processing(
        job.id, uow
    )

    assert updated_job.status == "processing"
    assert updated_job.started_at is not None


def test_start_ocr_job_processing_job_not_found(uow: FakeUnitOfWork):
    """Test that starting non-existent job raises error."""
    with pytest.raises(
        kul_ocr.adapters.database.repository.OCRJobNotFoundError,
        match="OCR job not found",
    ):
        _ = kul_ocr.service_layer.services.jobs.start_ocr_job_processing(
            str(uuid.uuid4()), uow
        )


def test_start_ocr_job_processing_already_processing(uow: FakeUnitOfWork):
    """Test that starting an already processing job is a no-op."""
    # Create a job that's already processing
    job = factories.generate_ocr_job(status=JobStatus.PROCESSING)
    original_started_at = job.started_at
    uow.jobs.add(job)

    # Attempting to start it again should be a no-op (same status transition)
    updated_job = kul_ocr.service_layer.services.jobs.start_ocr_job_processing(job.id, uow)

    assert updated_job.status == "processing"
    # Started_at should not change since it's the same status
    retrieved_job = uow.jobs.get(job.id)
    assert retrieved_job.started_at == original_started_at


# --- retry_failed_job tests ---


def test_retry_failed_job_success(uow: FakeUnitOfWork):
    """Test successfully retrying a failed job."""
    # Create a failed job
    failed_job = factories.generate_ocr_job(status=JobStatus.FAILED)
    failed_job.error_message = "Original error"
    uow.jobs.add(failed_job)

    # Retry the job - now returns JobDTO
    new_job_dto = kul_ocr.service_layer.services.jobs.retry_failed_job(
        failed_job.id, uow
    )

    assert new_job_dto.status == "pending"  # DTO has string status
    assert new_job_dto.id != failed_job.id
    assert new_job_dto.document_id == failed_job.document_id
    assert new_job_dto.error_message is None
    # Service no longer commits - that's the caller's responsibility


def test_retry_failed_job_not_found(uow: FakeUnitOfWork):
    """Test that retrying non-existent job raises error."""
    with pytest.raises(
        kul_ocr.adapters.database.repository.OCRJobNotFoundError,
        match="OCR job not found",
    ):
        _ = kul_ocr.service_layer.services.jobs.retry_failed_job("nonexistent-job", uow)


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

    with pytest.raises(
        exceptions.InvalidJobStatusTransitionErrorDepr,
        match="Invalid status transition",
    ):
        _ = kul_ocr.service_layer.services.jobs.retry_failed_job(job.id, uow)


# --- get_latest_result_for_document tests ---


def test_get_latest_result_for_document_success(uow: FakeUnitOfWork, tmp_path: Path):
    """Test getting the latest result for a document with multiple completed jobs."""
    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)
    document_id = document.id

    now = datetime.now(timezone.utc)
    # Create multiple completed jobs for the same document
    job1 = factories.generate_ocr_job(status=JobStatus.PENDING)
    job1.document_id = document_id
    job1.update_status(JobStatus.PROCESSING)
    job1.update_status(JobStatus.COMPLETED)
    job1.completed_at = now
    uow.jobs.add(job1)

    job2 = factories.generate_ocr_job(status=JobStatus.PENDING)
    job2.document_id = document_id
    job2.update_status(JobStatus.PROCESSING)
    job2.update_status(JobStatus.COMPLETED)
    job2.completed_at = now + timedelta(seconds=1)
    uow.jobs.add(job2)

    # Create results for both jobs
    result1 = factories.generate_ocr_result()
    result1.job_id = job1.id
    result2 = factories.generate_ocr_result()
    result2.job_id = job2.id
    uow.results.add(result1)
    uow.results.add(result2)

    # Get the latest result
    latest_result = (
        kul_ocr.service_layer.services.results.get_latest_result_for_document(
            document_id, uow
        )
    )

    # Should get the result from the most recent job (job2)
    assert latest_result is not None
    assert latest_result.job_id == job2.id
    # Service no longer commits - that's the caller's responsibility


def test_get_latest_result_for_document_no_completed_jobs(
    uow: FakeUnitOfWork, tmp_path: Path
):
    """Test that None is returned when document has no completed jobs."""
    document = factories.generate_document(tmp_path, file_type=FileType.PDF)
    uow.documents.add(document)
    document_id = document.id

    # Create only pending jobs
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.document_id = document_id
    uow.jobs.add(job)

    result = kul_ocr.service_layer.services.results.get_latest_result_for_document(
        document_id, uow
    )

    assert result is None


def test_get_latest_result_for_document_document_not_found(uow: FakeUnitOfWork):
    """Test that DocumentNotFoundError is raised when document has no jobs."""
    with pytest.raises(
        kul_ocr.adapters.database.repository.DocumentNotFoundError,
        match="Document not found",
    ):
        kul_ocr.service_layer.services.results.get_latest_result_for_document(
            "nonexistent-doc", uow
        )


# --- delete_ocr_job tests ---


def test_delete_completed_job_success(uow: FakeUnitOfWork):
    """Test successfully deleting a completed job."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    job.update_status(JobStatus.COMPLETED)
    uow.jobs.add(job)

    kul_ocr.service_layer.services.jobs.delete_ocr_job(job.id, uow)

    assert uow.jobs.get(job.id) is None
    assert uow.committed is True


def test_delete_failed_job_success(uow: FakeUnitOfWork):
    """Test successfully deleting a failed job."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.FAILED, error_message="Some error")
    uow.jobs.add(job)

    kul_ocr.service_layer.services.jobs.delete_ocr_job(job.id, uow)

    assert uow.jobs.get(job.id) is None
    assert uow.committed is True


def test_delete_pending_job_raises_error(uow: FakeUnitOfWork):
    """Test that deleting a pending job raises InvalidJobStatusTransitionErrorDepr."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    uow.jobs.add(job)

    with pytest.raises(
        exceptions.InvalidJobStatusTransitionError,
        match="cannot transition",
    ):
        kul_ocr.service_layer.services.jobs.delete_ocr_job(job.id, uow)


def test_delete_processing_job_raises_error(uow: FakeUnitOfWork):
    """Test that deleting a processing job raises InvalidJobStatusTransitionErrorDepr."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    uow.jobs.add(job)

    with pytest.raises(
        exceptions.InvalidJobStatusTransitionError,
        match="cannot transition",
    ):
        kul_ocr.service_layer.services.jobs.delete_ocr_job(job.id, uow)


def test_delete_nonexistent_job_raises_not_found(uow: FakeUnitOfWork):
    """Test that deleting non-existent job raises OCRJobNotFoundError."""
    with pytest.raises(
        kul_ocr.adapters.database.repository.OCRJobNotFoundError,
        match="OCR job not found",
    ):
        kul_ocr.service_layer.services.jobs.delete_ocr_job("nonexistent-job-id", uow)


def test_delete_job_also_deletes_associated_result(uow: FakeUnitOfWork):
    """Test that associated result is deleted with the job."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    job.update_status(JobStatus.COMPLETED)
    uow.jobs.add(job)

    result = factories.generate_ocr_result()
    result.job_id = job.id
    uow.results.add(result)

    kul_ocr.service_layer.services.jobs.delete_ocr_job(job.id, uow)

    assert uow.jobs.get(job.id) is None
    assert uow.results.get_by_job_id(job.id) is None
    assert uow.committed is True
