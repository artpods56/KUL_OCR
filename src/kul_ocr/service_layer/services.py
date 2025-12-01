import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from kul_ocr.domain import exceptions, model, ports
from kul_ocr.entrypoints import schemas
from kul_ocr.service_layer.uow import AbstractUnitOfWork


def generate_id() -> str:
    """Generates a unique identifier as a string.

    Creates a random UUID (version 4) used as an identifier for documents
    and OCR jobs within the system.

    Returns:
        A unique identifier represented as a string.
    """
    return str(uuid.uuid4())


# --- Document Services ---


def upload_document(
    file_stream: ports.FileStreamProtocol,
    file_size: int,
    file_type: model.FileType,
    storage: ports.FileStorage,
    uow: AbstractUnitOfWork,
) -> schemas.DocumentResponse:
    """Uploads a document to storage and saves it in the database.

    Saves the provided file stream to the storage system, generates a unique ID
    for the document, and persists its metadata in the database. If saving the
    file fails, the transaction is rolled back.

    Args:
        file_stream: A file-like object containing the document data.
        file_size: Size of the file in bytes.
        file_type: The type/format of the file (e.g., PDF, PNG).
        storage: Storage system used to save the file.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        A DocumentResponse schema representing the uploaded document.

    Raises:
        exceptions.FileUploadError: If saving the file to storage fails.
    """
    with uow:
        document_uuid = generate_id()
        storage_file_path = Path(document_uuid + file_type.dot_extension)

        try:
            document = model.Document(
                id=document_uuid,
                file_path=str(storage_file_path),
                file_type=file_type,
                file_size_bytes=file_size,
            )

            uow.documents.add(document)

            storage.save(stream=file_stream, file_path=storage_file_path)

            uow.commit()

            return schemas.DocumentResponse.from_domain(document)

        except exceptions.FileUploadError:
            uow.rollback()
            raise


# --- OCR Jobs Services ---


def get_ocr_jobs_by_status(
    status: model.JobStatus, uow: AbstractUnitOfWork
) -> Sequence[model.OCRJob]:
    """Gets OCR jobs filtered by status.

    Queries the database for all OCR jobs that match the given status. Useful
    for monitoring, reporting, or processing jobs in specific states (e.g.,
    PENDING, COMPLETED, FAILED).

    Args:
        status: The status to filter OCR jobs by.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        A sequence of OCRJob instances matching the given status.
    """
    with uow:
        ocr_jobs = uow.jobs.list_by_status(status)
        uow.commit()
        return ocr_jobs


def get_ocr_jobs_by_document_id(
    document_id: str, uow: AbstractUnitOfWork
) -> Sequence[model.OCRJob]:
    """Gets all OCR jobs for a specific document.

    Fetches all OCR jobs linked to the given document ID. Can be used to check
    the processing history or current status of a particular document's OCR tasks.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        A sequence of OCRJob instances associated with the specified document.
    """
    with uow:
        ocr_jobs = uow.jobs.list_by_document_id(document_id)
        uow.commit()
        return ocr_jobs


def get_terminal_ocr_jobs(uow: AbstractUnitOfWork) -> Sequence[model.OCRJob]:
    """Gets OCR jobs that are in a terminal state.

    Retrieves jobs that have reached a final state (COMPLETED or FAILED).
    Useful for reporting and monitoring.

    Args:
        uow: Unit of Work instance for managing database transactions.

    Returns:
        A sequence of OCRJob instances that have reached a terminal state.
    """
    with uow:
        ocr_jobs = uow.jobs.list_terminal_jobs()
        uow.commit()
        return ocr_jobs


def submit_ocr_job(document_id: str, uow: AbstractUnitOfWork) -> model.OCRJob:
    """Submits a new OCR processing job for a document.

    Creates a new OCR job in PENDING status for the specified document. The job
    will be picked up by a Celery worker for processing. Validates that the
    document exists before creating the job.

    Args:
        document_id: The unique identifier of the document to process.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        The newly created OCRJob instance in PENDING status.

    Raises:
        ValueError: If the document with the given ID does not exist.
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


def start_ocr_job_processing(job_id: str, uow: AbstractUnitOfWork) -> model.OCRJob:
    """Marks an OCR job as processing.

    Retrieves the OCR job by its ID, verifies that it exists, and updates its
    status to PROCESSING. Only jobs in PENDING status can be marked as
    processing. This is part of the workflow to track job progress.

    Args:
        job_id: The unique identifier of the OCR job to start processing.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        The OCRJob instance with its status updated to PROCESSING.

    Raises:
        ValueError: If the OCR job with the given ID does not exist.
    """
    with uow:
        ocr_job = uow.jobs.get(job_id)
        if ocr_job is None:
            raise ValueError(f"OCR Job {job_id} not found")

        # Domain model enforces business rules (must be PENDING)
        ocr_job.mark_as_processing()

        uow.commit()
        return ocr_job


def retry_failed_job(failed_job_id: str, uow: AbstractUnitOfWork) -> model.OCRJob:
    """Retries a previously failed OCR job.

    Checks that the original job exists and is in the FAILED status. Creates a
    new OCR job for the same document, allowing the OCR process to be retried
    without affecting the original failed job.

    Args:
        failed_job_id: The unique identifier of the failed OCR job.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        A new OCRJob instance in PENDING status for retrying the original job.

    Raises:
        ValueError: If the original job does not exist or is not in FAILED status.
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
    document_id: str, uow: AbstractUnitOfWork
) -> model.OCRResult[Any] | None:
    """Gets the most recent successful OCR result for a document.

    Finds all completed OCR jobs for the given document, selects the most
    recently finished job, and returns its result. Returns None if no completed
    jobs exist.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        The OCRResult of the latest completed job, or None if no completed jobs exist.
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
    document_id: str, uow: AbstractUnitOfWork
) -> tuple[model.Document, model.OCRResult[Any] | None]:
    """Gets a document along with its latest OCR result, if available.

    Fetches the document by ID and finds the most recent completed OCR job for
    it. Returns the OCR result alongside the document; if no completed jobs
    exist, the result is None.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance for managing database transactions.

    Returns:
        A tuple containing the Document instance and the latest OCRResult
        (or None if no completed OCR jobs exist).

    Raises:
        ValueError: If the document with the given ID does not exist.
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
