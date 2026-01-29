import time

import pytest

from core.domain import exceptions
from core.domain.model import Job
from core.domain.enums import JobStatus


class TestOCRJob:
    def test_job_initialization(self):
        job = Job(document_id="test-doc", id="test-init")
        assert job.id == "test-init"
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None
        assert job.error_message is None
        assert job.started_at is None
        assert job.completed_at is None

    def test_update_job_to_processing(self):
        job = Job(document_id="test-doc", id="test-job-update-to-processing")
        job.update_status(JobStatus.PROCESSING)
        assert job.status == JobStatus.PROCESSING
        assert job.started_at is not None
        assert job.completed_at is None

    def test_update_job_to_completed(self):
        job = Job(document_id="test-doc", id="test-job-completion")
        job.update_status(JobStatus.PROCESSING)
        time.sleep(0.001)
        job.update_status(JobStatus.COMPLETED)

        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.created_at < job.completed_at
        assert job.error_message is None

    def test_update_job_to_failed(self):
        job = Job(document_id="test-doc", id="test-job-update-to-failed")
        error_message = "error-message"
        job.update_status(JobStatus.FAILED, error_message=error_message)

        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None
        assert job.error_message == error_message

    def test_update_to_same_status_is_noop(self):
        job = Job(document_id="test-doc", id="test-job-update-same-status")
        job.update_status(JobStatus.PROCESSING)
        assert job.status == JobStatus.PROCESSING
        started_at_first = job.started_at

        # Updating to the same status should be a no-op
        job.update_status(JobStatus.PROCESSING)
        assert job.status == JobStatus.PROCESSING
        assert job.started_at == started_at_first  # Timestamp shouldn't change

    def test_cannot_complete_pending_job(self):
        job = Job(document_id="test-doc", id="test-job-update-pending-to-completed")
        with pytest.raises(exceptions.InvalidJobStatusTransitionError) as excinfo:
            job.update_status(JobStatus.COMPLETED)
            assert "not a processed job" in str(excinfo.value)

    def test_job_is_terminal(self):
        job = Job(document_id="test-doc", id="test-job-is-terminal")
        job.update_status(JobStatus.PROCESSING)
        job.update_status(JobStatus.COMPLETED)

        assert job.is_terminal, "Job is already in a terminal state"

        # Cannot transition from terminal state to another state
        with pytest.raises(exceptions.InvalidJobStatusTransitionError):
            job.update_status(JobStatus.PROCESSING)

    def test_job_can_fail_before_completion(self):
        pending_job = Job(document_id="test-doc", id="test-fail-pending-job")
        pending_job.update_status(JobStatus.FAILED, error_message="fail-pending")
        assert pending_job.status == JobStatus.FAILED
        assert pending_job.is_terminal

        processing_job = Job(document_id="test-doc", id="test-fail-processing-job")
        processing_job.update_status(JobStatus.FAILED, error_message="fail-processing")
        assert processing_job.status == JobStatus.FAILED
        assert processing_job.is_terminal

    def test_job_completion_time(self):
        job1 = Job(document_id="test-doc", id="test-timing-job-1")
        time.sleep(0.001)
        job2 = Job(document_id="test-doc", id="test-timing-job-2")

        job1.update_status(JobStatus.PROCESSING)
        time.sleep(0.0001)
        job2.update_status(JobStatus.PROCESSING)

        job2.update_status(JobStatus.COMPLETED)
        time.sleep(0.0001)
        job1.update_status(JobStatus.COMPLETED)

        assert job1.completed_at is not None
        assert job2.completed_at is not None
        assert job1.started_at is not None
        assert job2.started_at is not None

        assert job1.created_at < job2.created_at, "job1 got created first"
        assert job1.completed_at > job2.completed_at, "job2 got completed first"
        assert job1.started_at < job2.started_at, "job2 started before job1"
        assert job1.duration > job2.duration, "job1 run longer than job2"
