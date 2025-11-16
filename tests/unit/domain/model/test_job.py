import time

import pytest

from ocr_kul.domain.model import OCRJob, JobStatus


class TestOCRJob:
    def test_job_initialization(self):
        job = OCRJob(document_id="test-doc", id="test-init")
        assert job.id == "test-init"
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None
        assert job.error_message is None
        assert job.started_at is None
        assert job.completed_at is None

    def test_mark_job_as_processing(self):
        job = OCRJob(document_id="test-doc", id="test-job-mark-as-processing")
        job.mark_as_processing()
        assert job.status == JobStatus.PROCESSING
        assert job.started_at is not None
        assert job.completed_at is None

    def test_mark_job_as_completed(self):
        job = OCRJob(document_id="test-doc", id="test-job-completion")
        job.mark_as_processing()

        job.complete()

        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.created_at < job.completed_at
        assert job.error_message is None

    def test_mark_job_as_failed(self):
        job = OCRJob(document_id="test-doc", id="test-job-mark-as-failed")
        error_message = "error-message"
        job.fail(error_message=error_message)

        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None
        assert job.error_message == error_message

    def test_cannot_mark_processing_as_processing(self):
        job = OCRJob(document_id="test-doc", id="test-job-mark-as-processing")
        job.mark_as_processing()
        assert job.status == JobStatus.PROCESSING

        with pytest.raises(RuntimeError) as excinfo:
            job.mark_as_processing()
            assert "already been processed" in str(excinfo.value)
            assert job.status == JobStatus.PROCESSING

    def test_cannot_complete_pending_job(self):
        job = OCRJob(document_id="test-doc", id="test-job-mark-as-processing")
        with pytest.raises(RuntimeError) as excinfo:
            job.complete()
            assert "not a processed job" in str(excinfo.value)

    def test_job_is_terminal(self):
        job = OCRJob(document_id="test-doc", id="test-job-is-terminal")
        job.mark_as_processing()
        job.complete()

        with pytest.raises(RuntimeError) as excinfo:
            assert job.is_terminal, "Job is already in a terminal state"
            job.complete()
            assert "can only complete processed jobs" in str(excinfo.value)

    def test_job_can_fail_before_completion(self):
        pending_job = OCRJob(document_id="test-doc", id="test-fail-pending-job")
        pending_job.fail("fail-pending")
        assert pending_job.status == JobStatus.FAILED
        assert pending_job.is_terminal

        processing_job = OCRJob(document_id="test-doc", id="test-fail-processing-job")
        processing_job.fail("fail-processing")
        assert processing_job.status == JobStatus.FAILED
        assert processing_job.is_terminal

    def test_job_completion_time(self):
        job1 = OCRJob(document_id="test-doc", id="test-timing-job-1")
        time.sleep(0.001)
        job2 = OCRJob(document_id="test-doc", id="test-timing-job-2")

        job1.mark_as_processing()
        job2.mark_as_processing()

        job2.complete()
        time.sleep(0.0001)
        job1.complete()

        assert job1.completed_at is not None
        assert job2.completed_at is not None
        assert job1.started_at is not None
        assert job2.started_at is not None

        assert job1.created_at < job2.created_at, "job1 got created first"
        assert job1.completed_at > job2.completed_at, "job2 got completed first"
        assert job1.started_at < job2.started_at, "job2 started before job1"
        assert job1.duration > job2.duration, "job1 run longer than job2"
