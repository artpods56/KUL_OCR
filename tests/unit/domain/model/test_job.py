import time

import pytest

from datetime import datetime
from kul_ocr.domain.model import OCRJob, JobStatus


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
        time.sleep(0.001)
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
        time.sleep(0.0001)
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

    def test_job_duration_raises_when_pending(self):
        job = OCRJob(id="1", document_id="doc-1", status=JobStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot calculate duration for job 1"):
            _ = job.duration

    def test_job_duration_raises_when_processing(self):
        job = OCRJob(id="2", document_id="doc-2", status=JobStatus.PROCESSING)
        with pytest.raises(ValueError, match="Cannot calculate duration for job 2"):
            _ = job.duration

    def test_job_cannot_fail_after_completed(self):
        job = OCRJob(id="3", document_id="doc-3", status=JobStatus.COMPLETED, started_at=datetime.now(),
                     completed_at=datetime.now())
        with pytest.raises(RuntimeError, match="Cannot fail job 3 - job is already in a terminal state JobStatus.COMPLETED"):
            job.fail("error")

    def test_job_cannot_fail_after_failed(self):
        job = OCRJob(id="4", document_id="doc-4", status=JobStatus.FAILED, started_at=datetime.now(),
                     completed_at=datetime.now())
        with pytest.raises(RuntimeError, match="Cannot fail job 4 - job is already in a terminal state JobStatus.FAILED"):
            job.fail("error")

    def test_job_fail_with_empty_error_message(self):
        job = OCRJob(id="5", document_id="doc-5")
        job.fail("")
        assert job.status == JobStatus.FAILED
        assert job.error_message == ""

    def test_job_fail_with_very_long_error_message(self):
        long_msg = "x" * 10000
        job = OCRJob(id="6", document_id="doc-6")
        job.fail(long_msg)
        assert job.status == JobStatus.FAILED
        assert job.error_message == long_msg
