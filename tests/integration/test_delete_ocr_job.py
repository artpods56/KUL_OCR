import pytest

import core.adapters.database.repository
from backend.jobs import service
from core.domain import exceptions
from core.domain.model import (
    BoundingBox,
    Document,
    Job,
    PageMetadata,
    PagePart,
    PageRef,
    ProcessedPage,
    Result,
    TextPart,
)
from core.domain.enums import JobStatus, FileType
from core.utils.misc import generate_id
from core.adapters.database.uow import SqlAlchemyUnitOfWork


def _create_job_with_document(
    uow: SqlAlchemyUnitOfWork, status: JobStatus = JobStatus.PENDING
) -> tuple[str, str]:
    """Helper to create a document and job for testing."""
    document_id = generate_id()
    job_id = generate_id()

    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    job = Job(id=job_id, document_id=document_id, status=status)

    with uow:
        uow.documents.add(document)
        uow.jobs.add(job)
        uow.commit()

    return document_id, job_id


def _create_job_with_result(uow: SqlAlchemyUnitOfWork) -> tuple[str, str, str]:
    """Helper to create a completed job with associated result."""
    document_id = generate_id()
    job_id = generate_id()
    result_id = generate_id()

    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    job = Job(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    processed_page = ProcessedPage(
        ref=PageRef(document_id=document_id, index=0),
        result=PagePart(
            parts=[
                TextPart(
                    text="OCR text content",
                    bbox=BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0),
                    confidence=0.95,
                    level="block",
                )
            ],
            metadata=PageMetadata(page_number=1, width=100, height=50),
        ),
    )

    result = Result(id=result_id, job_id=job_id, content=[processed_page])

    with uow:
        uow.documents.add(document)
        uow.jobs.add(job)
        job.update_status(JobStatus.PROCESSING)
        job.update_status(JobStatus.COMPLETED)
        uow.results.add(result)
        uow.commit()

    return document_id, job_id, result_id


class TestDeleteOCRJobIntegration:
    """Integration tests for delete_ocr_job service function."""

    def test_delete_completed_job_removes_from_database(
        self, uow: SqlAlchemyUnitOfWork
    ):
        """Test that deleting a completed job removes it from the database."""
        document_id, job_id = _create_job_with_document(uow, JobStatus.PENDING)

        with uow:
            job = uow.jobs.get(job_id)
            assert job is not None
            job.update_status(JobStatus.PROCESSING)
            job.update_status(JobStatus.COMPLETED)
            uow.commit()

        service.delete_ocr_job(job_id, uow)

        with uow:
            deleted_job = uow.jobs.get(job_id)
            assert deleted_job is None

    def test_delete_failed_job_removes_from_database(self, uow: SqlAlchemyUnitOfWork):
        """Test that deleting a failed job removes it from the database."""
        document_id, job_id = _create_job_with_document(uow, JobStatus.PENDING)

        with uow:
            job = uow.jobs.get(job_id)
            assert job is not None
            job.update_status(JobStatus.FAILED, error_message="Test error")
            uow.commit()

        service.delete_ocr_job(job_id, uow)

        with uow:
            deleted_job = uow.jobs.get(job_id)
            assert deleted_job is None

    def test_delete_pending_job_raises_invalid_status_error(
        self, uow: SqlAlchemyUnitOfWork
    ):
        """Test that deleting a pending job raises InvalidJobStatusTransitionError."""
        document_id, job_id = _create_job_with_document(uow, JobStatus.PENDING)

        with pytest.raises(
            exceptions.InvalidJobStatusTransitionError,
            match="cannot transition",
        ):
            service.delete_ocr_job(job_id, uow)

        with uow:
            job = uow.jobs.get(job_id)
            assert job is not None

    def test_delete_processing_job_raises_invalid_status_error(
        self, uow: SqlAlchemyUnitOfWork
    ):
        """Test that deleting a processing job raises InvalidJobStatusTransitionError."""
        document_id, job_id = _create_job_with_document(uow, JobStatus.PENDING)

        with uow:
            job = uow.jobs.get(job_id)
            assert job is not None
            job.update_status(JobStatus.PROCESSING)
            uow.commit()

        with pytest.raises(
            exceptions.InvalidJobStatusTransitionError,
            match="cannot transition",
        ):
            service.delete_ocr_job(job_id, uow)

        with uow:
            job = uow.jobs.get(job_id)
            assert job is not None

    def test_delete_nonexistent_job_raises_not_found_error(
        self, uow: SqlAlchemyUnitOfWork
    ):
        """Test that deleting a non-existent job raises OCRJobNotFoundError."""
        fake_job_id = generate_id()

        with pytest.raises(
            core.adapters.database.repository.OCRJobNotFoundError,
            match="OCR job not found",
        ):
            service.delete_ocr_job(fake_job_id, uow)

    def test_delete_job_also_deletes_associated_result(self, uow: SqlAlchemyUnitOfWork):
        """Test that deleting a job also deletes the associated Result."""
        document_id, job_id, result_id = _create_job_with_result(uow)

        with uow:
            result = uow.results.get(result_id)
            assert result is not None

        service.delete_ocr_job(job_id, uow)

        with uow:
            deleted_job = uow.jobs.get(job_id)
            deleted_result = uow.results.get(result_id)
            assert deleted_job is None
            assert deleted_result is None

    def test_delete_job_does_not_affect_document(self, uow: SqlAlchemyUnitOfWork):
        """Test that deleting a job does not delete the associated document."""
        document_id, job_id, result_id = _create_job_with_result(uow)

        service.delete_ocr_job(job_id, uow)

        with uow:
            document = uow.documents.get(document_id)
            assert document is not None
