import uuid
from typing import Any

from ocr_kul.domain import model
from ocr_kul.service_layer import uow


def generate_id() -> str:
    return str(uuid.uuid4())


# --- Document Services ---


def upload_document(
    file_path: str, file_type: model.FileType, uow: uow.AbstractUnitOfWork
) -> model.Document:
    with uow:
        document = model.Document(
            id=generate_id(), file_path=file_path, file_type=file_type
        )
        uow.documents.add(document)
        uow.commit()
        return document


# --- OCR Jobs Services ---


def get_ocr_jobs_by_status(
    status: model.JobStatus, uow: uow.AbstractUnitOfWork
) -> list[model.OCRJob]:
    with uow:
        ocr_jobs = uow.jobs.list_by_status(status)
        uow.commit()
        return ocr_jobs


def get_ocr_jobs_by_document_id(
    document_id: str, uow: uow.AbstractUnitOfWork
) -> list[model.OCRJob]:
    with uow:
        ocr_jobs = uow.jobs.list_by_document_id(document_id)
        uow.commit()
        return ocr_jobs


def get_terminal_ocr_jobs(uow: uow.AbstractUnitOfWork) -> list[model.OCRJob]:
    with uow:
        ocr_jobs = uow.jobs.list_terminal_jobs()
        uow.commit()
        return ocr_jobs


def submit_ocr_job(document_id: str, uow: uow.AbstractUnitOfWork) -> model.OCRJob:
    """
    Submit a new OCR job for a document.
    Business process: validates document exists, creates job, and persists it.
    """
    with uow:
        # Verify document exists
        document = uow.documents.get(document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        # Create new OCR job
        ocr_job = model.OCRJob(id=generate_id(), document_id=document_id)

        uow.jobs.add(ocr_job)
        uow.commit()
        return ocr_job


def start_ocr_job_processing(job_id: str, uow: uow.AbstractUnitOfWork) -> model.OCRJob:
    """
    Mark a job as processing.
    Business process: retrieves job, validates state, marks as processing.
    """
    with uow:
        ocr_job = uow.jobs.get(job_id)
        if ocr_job is None:
            raise ValueError(f"OCR Job {job_id} not found")

        # Domain model enforces business rules (must be PENDING)
        ocr_job.mark_as_processing()

        uow.commit()
        return ocr_job


def retry_failed_job(failed_job_id: str, uow: uow.AbstractUnitOfWork) -> model.OCRJob:
    """
    Create a new job to retry a failed OCR job.
    Business process: validates original job failed, creates new job for same document.
    """
    with uow:
        original_job = uow.jobs.get(failed_job_id)
        if original_job is None:
            raise ValueError(f"OCR Job {failed_job_id} not found")

        if original_job.status != model.JobStatus.FAILED:
            raise ValueError(
                f"Cannot retry job {failed_job_id} - job status is {original_job.status}, ",
                "only failed jobs can be retried",
            )

        # Create new job for the same document
        new_job = model.OCRJob(id=generate_id(), document_id=original_job.document_id)

        uow.jobs.add(new_job)
        uow.commit()
        return new_job


def get_latest_result_for_document(
    document_id: str, uow: uow.AbstractUnitOfWork
) -> model.OCRResult[Any] | None:
    """
    Get the most recent successful OCR result for a document.
    Business process: finds completed jobs, gets latest, retrieves result.
    """
    with uow:
        # Get all completed jobs for this document
        jobs = uow.jobs.list_by_document_id(document_id)
        completed_jobs = [j for j in jobs if j.status == model.JobStatus.COMPLETED]

        if not completed_jobs:
            return None

        # Get the most recent completed job
        latest_job = max(completed_jobs, key=lambda j: j.completed_at or j.created_at)

        # Get all results and find the one for this job
        all_results = uow.results.list_all()
        job_result = next((r for r in all_results if r.job_id == latest_job.id), None)

        uow.commit()
        return job_result


# --- Document Services ---


def get_document_with_latest_result(
    document_id: str, uow: uow.AbstractUnitOfWork
) -> tuple[model.Document, model.OCRResult | None]:
    """
    Get a document along with its latest OCR result if available.
    Business process: retrieves document and coordinates getting latest result.
    """
    with uow:
        document = uow.documents.get(document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        # Get all completed jobs for this document
        jobs = uow.jobs.list_by_document_id(document_id)
        completed_jobs = [j for j in jobs if j.status == model.JobStatus.COMPLETED]

        latest_result = None
        if completed_jobs:
            # Get the most recent completed job
            latest_job = max(
                completed_jobs, key=lambda j: j.completed_at or j.created_at
            )

            # Get all results and find the one for this job
            all_results = uow.results.list_all()
            latest_result = next(
                (r for r in all_results if r.job_id == latest_job.id), None
            )

        uow.commit()
        return document, latest_result
