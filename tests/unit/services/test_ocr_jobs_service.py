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
        exceptions.InvalidJobStatusTransitionError,
        match="cannot transition",
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
    """Test that deleting a pending job raises InvalidJobStatusTransitionError."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    uow.jobs.add(job)

    with pytest.raises(
        exceptions.InvalidJobStatusTransitionError,
        match="cannot transition",
    ):
        kul_ocr.service_layer.services.jobs.delete_ocr_job(job.id, uow)


def test_delete_processing_job_raises_error(uow: FakeUnitOfWork):
    """Test that deleting a processing job raises InvalidJobStatusTransitionError."""
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


# --- cancel_ocr_job tests ---


def test_cancel_pending_job(uow: FakeUnitOfWork):
    """Test cancelling a PENDING job marks it as FAILED with cancellation message."""
    from tests.fakes.task_runner import FakeTaskRunner

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    uow.jobs.add(job)

    task_runner = FakeTaskRunner()
    result_dto = kul_ocr.service_layer.services.jobs.cancel_ocr_job(
        job_id=job.id, task_runner=task_runner, uow=uow
    )

    # Verify job is marked as FAILED
    assert result_dto.status == JobStatus.FAILED.value
    assert result_dto.error_message is not None
    assert "cancel" in result_dto.error_message.lower()

    # Verify no task revocation attempted (PENDING job has no task)
    assert len(task_runner.revoked_tasks) == 0

    # Verify changes committed
    assert uow.committed is True


def test_cancel_processing_job_with_task_id(uow: FakeUnitOfWork):
    """Test cancelling a PROCESSING job with task_id revokes the task."""
    from tests.fakes.task_runner import FakeTaskRunner
    from kul_ocr.domain import model
    from kul_ocr.domain.enums import OutboxEventType

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    task_id = "test-task-id-123"
    job.assign_task_id(task_id)
    uow.jobs.add(job)

    # Add outbox entry for outbox cleanup path
    outbox_entry = model.OutboxEntry(
        id=task_id,
        event_type=OutboxEventType.JOB_SCHEDULING,
        aggregate_id=job.id,
        payload={"job_id": job.id},
    )
    uow.outbox.add(outbox_entry)

    task_runner = FakeTaskRunner()
    result_dto = kul_ocr.service_layer.services.jobs.cancel_ocr_job(
        job_id=job.id, task_runner=task_runner, uow=uow
    )

    # Verify job is marked as FAILED
    assert result_dto.status == JobStatus.FAILED.value
    assert result_dto.error_message is not None
    assert "cancel" in result_dto.error_message.lower()

    # Verify task was revoked
    assert task_id in task_runner.revoked_tasks

    # Verify changes committed
    assert uow.committed is True


def test_cancel_processing_job_without_task_id_still_cancels(uow: FakeUnitOfWork):
    """Test cancelling a PROCESSING job without task_id still cancels successfully.

    Since task_id is None, no revocation is attempted, but the job is still
    marked as FAILED and changes are committed.
    """
    from tests.fakes.task_runner import FakeTaskRunner

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    # task_id is None
    uow.jobs.add(job)

    task_runner = FakeTaskRunner()

    result_dto = kul_ocr.service_layer.services.jobs.cancel_ocr_job(
        job_id=job.id, task_runner=task_runner, uow=uow
    )

    # Job successfully updated to FAILED
    assert result_dto.status == JobStatus.FAILED.value
    assert result_dto.error_message is not None
    assert "cancel" in result_dto.error_message.lower()

    # No task revocation occurred (no task_id)
    assert len(task_runner.revoked_tasks) == 0

    # Changes are committed
    assert uow.committed is True


def test_cancel_completed_job_returns_unchanged(uow: FakeUnitOfWork):
    """Test cancelling a COMPLETED job returns it unchanged."""
    from tests.fakes.task_runner import FakeTaskRunner

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    job.update_status(JobStatus.COMPLETED)
    uow.jobs.add(job)

    task_runner = FakeTaskRunner()
    result_dto = kul_ocr.service_layer.services.jobs.cancel_ocr_job(
        job_id=job.id, task_runner=task_runner, uow=uow
    )

    # Job should remain COMPLETED
    assert result_dto.status == JobStatus.COMPLETED.value
    assert result_dto.error_message is None

    # No revocation should occur
    assert len(task_runner.revoked_tasks) == 0


def test_cancel_failed_job_returns_unchanged(uow: FakeUnitOfWork):
    """Test cancelling a FAILED job returns it unchanged."""
    from tests.fakes.task_runner import FakeTaskRunner

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.FAILED, error_message="Previous error")
    uow.jobs.add(job)

    task_runner = FakeTaskRunner()
    result_dto = kul_ocr.service_layer.services.jobs.cancel_ocr_job(
        job_id=job.id, task_runner=task_runner, uow=uow
    )

    # Job should remain FAILED with original error
    assert result_dto.status == JobStatus.FAILED.value
    assert result_dto.error_message == "Previous error"

    # No revocation should occur
    assert len(task_runner.revoked_tasks) == 0


def test_cancel_nonexistent_job_raises_not_found(uow: FakeUnitOfWork):
    """Test cancelling non-existent job raises OCRJobNotFoundError."""
    from tests.fakes.task_runner import FakeTaskRunner

    task_runner = FakeTaskRunner()

    with pytest.raises(
        kul_ocr.adapters.database.repository.OCRJobNotFoundError,
        match="OCR job not found",
    ):
        kul_ocr.service_layer.services.jobs.cancel_ocr_job(
            job_id="nonexistent-job-id", task_runner=task_runner, uow=uow
        )


def test_cancel_job_with_relayed_outbox_entry_revokes_task(uow: FakeUnitOfWork):
    """Test cancelling job with relayed outbox entry also revokes via outbox cleanup path."""
    from tests.fakes.task_runner import FakeTaskRunner
    from kul_ocr.domain import model
    from kul_ocr.domain.enums import OutboxEventType

    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    task_id = "outbox-task-id"
    job.assign_task_id(task_id)
    uow.jobs.add(job)

    # Create outbox entry that's been relayed
    outbox_entry = model.OutboxEntry(
        id=task_id,
        event_type=OutboxEventType.JOB_SCHEDULING,
        aggregate_id=job.id,
        payload={"job_id": job.id},
    )
    outbox_entry.mark_as_relayed()
    uow.outbox.add(outbox_entry)

    task_runner = FakeTaskRunner()
    result_dto = kul_ocr.service_layer.services.jobs.cancel_ocr_job(
        job_id=job.id, task_runner=task_runner, uow=uow
    )

    # Verify job cancelled
    assert result_dto.status == JobStatus.FAILED.value

    # Verify task was revoked via outbox cleanup path
    assert task_id in task_runner.revoked_tasks

    # Verify changes committed
    assert uow.committed is True


# --- complete_ocr_job tests ---


def test_complete_ocr_job_saves_result_and_marks_completed(uow: FakeUnitOfWork):
    """Test that complete_ocr_job saves result and marks job as COMPLETED."""
    from kul_ocr.domain.structs import ResultDTO

    # Create a PROCESSING job
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    uow.jobs.add(job)

    # Create a result
    result = factories.generate_ocr_result()
    result_dto = ResultDTO.from_domain(result)

    # Complete the job
    completed_dto = kul_ocr.service_layer.services.jobs.complete_ocr_job(
        job_id=job.id, result_dto=result_dto, uow=uow
    )

    # Verify job marked as COMPLETED
    assert completed_dto.status == JobStatus.COMPLETED.value
    assert completed_dto.id == job.id

    # Verify result was saved
    with uow:
        saved_result = uow.results.get_by_job_id(job.id)
        assert saved_result is not None
        assert saved_result.job_id == job.id
        assert len(saved_result.content) == len(result.content)


def test_complete_ocr_job_nonexistent_job_raises_not_found(uow: FakeUnitOfWork):
    """Test that completing non-existent job raises OCRJobNotFoundError."""
    from kul_ocr.domain.structs import ResultDTO

    result = factories.generate_ocr_result()
    result_dto = ResultDTO.from_domain(result)

    with pytest.raises(
        kul_ocr.adapters.database.repository.OCRJobNotFoundError,
        match="OCR job not found",
    ):
        kul_ocr.service_layer.services.jobs.complete_ocr_job(
            job_id="nonexistent-job-id", result_dto=result_dto, uow=uow
        )


# --- fail_ocr_job tests ---


def test_fail_ocr_job_marks_as_failed_with_error_message(uow: FakeUnitOfWork):
    """Test that fail_ocr_job marks job as FAILED with error message."""
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.update_status(JobStatus.PROCESSING)
    uow.jobs.add(job)

    error_message = "OCR processing failed due to timeout"

    failed_dto = kul_ocr.service_layer.services.jobs.fail_ocr_job(
        job_id=job.id, error_message=error_message, uow=uow
    )

    # Verify job marked as FAILED
    assert failed_dto.status == JobStatus.FAILED.value
    assert failed_dto.error_message == error_message

    # Verify changes committed
    assert uow.committed is True


def test_fail_ocr_job_nonexistent_job_raises_not_found(uow: FakeUnitOfWork):
    """Test that failing non-existent job raises OCRJobNotFoundError."""
    with pytest.raises(
        kul_ocr.adapters.database.repository.OCRJobNotFoundError,
        match="OCR job not found",
    ):
        kul_ocr.service_layer.services.jobs.fail_ocr_job(
            job_id="nonexistent-job-id", error_message="Test error", uow=uow
        )


# --- submit_ocr_job duplicate detection tests ---


def test_submit_ocr_job_raises_error_when_active_job_exists(uow: FakeUnitOfWork):
    """Test that submitting job for document with active job raises DuplicateOCRJobError."""
    # Create document
    document = factories.generate_document_without_file()
    uow.documents.add(document)

    # Create first job (active)
    first_job = factories.generate_ocr_job(status=JobStatus.PENDING)
    first_job.document_id = document.id
    uow.jobs.add(first_job)

    # Try to submit second job for same document
    with pytest.raises(
        kul_ocr.service_layer.services.jobs.DuplicateOCRJobError,
        match=f"Document {document.id} already has a pending or active job",
    ):
        kul_ocr.service_layer.services.jobs.submit_ocr_job(
            document_id=document.id, uow=uow
        )


def test_submit_ocr_job_succeeds_when_previous_job_completed(uow: FakeUnitOfWork):
    """Test that submitting job succeeds when previous job is COMPLETED."""
    # Create document
    document = factories.generate_document_without_file()
    uow.documents.add(document)

    # Create first job and complete it
    first_job = factories.generate_ocr_job(status=JobStatus.PENDING)
    first_job.document_id = document.id
    first_job.update_status(JobStatus.PROCESSING)
    first_job.update_status(JobStatus.COMPLETED)
    uow.jobs.add(first_job)

    # Submit second job for same document (should succeed)
    second_job_dto = kul_ocr.service_layer.services.jobs.submit_ocr_job(
        document_id=document.id, uow=uow
    )

    # Verify second job created
    assert second_job_dto.document_id == document.id
    assert second_job_dto.id != first_job.id
    assert second_job_dto.status == JobStatus.PENDING.value


def test_submit_ocr_job_succeeds_when_previous_job_failed(uow: FakeUnitOfWork):
    """Test that submitting job succeeds when previous job is FAILED."""
    # Create document
    document = factories.generate_document_without_file()
    uow.documents.add(document)

    # Create first job and fail it
    first_job = factories.generate_ocr_job(status=JobStatus.PENDING)
    first_job.document_id = document.id
    first_job.update_status(JobStatus.FAILED, error_message="Test failure")
    uow.jobs.add(first_job)

    # Submit second job for same document (should succeed)
    second_job_dto = kul_ocr.service_layer.services.jobs.submit_ocr_job(
        document_id=document.id, uow=uow
    )

    # Verify second job created
    assert second_job_dto.document_id == document.id
    assert second_job_dto.id != first_job.id
    assert second_job_dto.status == JobStatus.PENDING.value
