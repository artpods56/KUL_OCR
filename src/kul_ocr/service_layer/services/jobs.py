from collections.abc import Sequence

from kul_ocr.domain import structs, model, enums, exceptions
from kul_ocr.domain.protocols import TaskRunner
from kul_ocr.domain.exceptions import DomainException
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.uow import AbstractUnitOfWork

from kul_ocr.utils.logger import get_logger

logger = get_logger(__name__)


def get_ocr_job(job_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Gets an OCR job by its ID.

    Args:
        job_id: The unique identifier of the OCR job.
        uow: Unit of Work instance.

    Returns:
        The JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the job does not exist.
    """
    with uow:
        return structs.JobDTO.from_domain(uow.jobs.get_or_raise(job_id))


def get_ocr_job_response(job_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Gets an OCR job by its ID and returns it as a DTO.

    Args:
        job_id: The unique identifier of the OCR job.
        uow: Unit of Work instance.

    Returns:
        The JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the job does not exist.
    """
    with uow:
        return structs.JobDTO.from_domain(uow.jobs.get_or_raise(job_id))


def get_ocr_jobs_by_status(
    status: enums.JobStatus, uow: AbstractUnitOfWork
) -> Sequence[structs.JobDTO]:
    """Gets OCR jobs filtered by status.

    Queries the database for all OCR jobs that match the given status. Useful
    for monitoring, reporting, or processing jobs in specific states (e.g.,
    PENDING, COMPLETED, FAILED).

    Args:
        status: The status to filter OCR jobs by.
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A sequence of JobDTO instances matching the given status.
    """
    with uow:
        jobs = uow.jobs.list_by_status(status)
        return [structs.JobDTO.from_domain(job) for job in jobs]


def get_ocr_jobs_by_document_id(
    document_id: str, uow: AbstractUnitOfWork
) -> Sequence[structs.JobDTO]:
    """Gets all OCR jobs for a specific document.

    Fetches all OCR jobs linked to the given document ID. Can be used to check
    the processing history or current status of a particular document's OCR tasks.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A sequence of JobDTO instances associated with the specified document.
    """
    with uow:
        jobs = uow.jobs.list_by_document_id(document_id)
        return [structs.JobDTO.from_domain(job) for job in jobs]


def get_ocr_jobs(
    uow: AbstractUnitOfWork,
    status: str | None = None,
    document_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[Sequence[structs.JobDTO], int]:
    """Gets OCR jobs with optional filtering and pagination.

    Args:
        uow: Unit of Work instance.
        status: Optional status to filter by.
        document_id: Optional document ID to filter by.
        skip: Number of items to skip (offset).
        limit: Maximum number of items to return.

    Returns:
        Tuple of (job DTOs, total count).

    Raises:
        exceptions.UnknownJobStatusError: If invalid status provided.
    """
    with uow:
        if status:
            if status not in [s.value for s in enums.JobStatus]:
                raise exceptions.UnknownJobStatusError(status=status)

        job_status = enums.JobStatus(status) if status else None

        # Get paginated jobs
        jobs = uow.jobs.list_by_filters(
            status=job_status,
            document_id=document_id,
            skip=skip,
            limit=limit,
        )

        # Get total count
        total = uow.jobs.count_by_filters(
            status=job_status,
            document_id=document_id,
        )

        return [structs.JobDTO.from_domain(job) for job in jobs], total


def get_terminal_ocr_jobs(uow: AbstractUnitOfWork) -> Sequence[structs.JobDTO]:
    """Gets OCR jobs that are in a terminal state.

    Retrieves jobs that have reached a final state (COMPLETED or FAILED).
    Useful for reporting and monitoring.

    Args:
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A sequence of JobDTO instances that have reached a terminal state.
    """
    jobs = uow.jobs.list_terminal_jobs()
    return [structs.JobDTO.from_domain(job) for job in jobs]


def delete_ocr_job(job_id: str, uow: AbstractUnitOfWork) -> None:
    """Deletes an OCR job in terminal state.

    Only jobs that have reached a terminal state (COMPLETED, FAILED) can be deleted.
    Associated Result records are also deleted for complete cleanup.

    Args:
        job_id: The unique identifier of the OCR job.
        uow: Unit of Work instance.

    Raises:
        exceptions.OCRJobNotFoundError: If the job does not exist.
        exceptions.InvalidJobStatusTransitionError: If the job is not in terminal state.
    """
    with uow:
        job = uow.jobs.get_or_raise(job_id)

        # Business rule validation stays in service
        if not job.is_terminal:
            raise exceptions.InvalidJobStatusTransitionError(
                job_id=job_id,
                current=job.status,
                attempted=model.JobStatus.FAILED,
                reason="Cannot delete non-terminal jobs.",
            )

        # Repository handles cascade
        uow.jobs.delete_with_cascade(job)
        uow.commit()

        logger.info("Deleted OCR job", job_id=job_id, status=job.status.value)


def submit_ocr_job(document_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Submits a new OCR processing job for a document.

    Creates a new OCR job in PENDING status for the specified document.

    Args:
        document_id: The unique identifier of the document to process.
        uow: Unit of Work instance.

    Returns:
        The created JobDTO.

    Raises:
        exceptions.DocumentNotFoundError: If the document with the given ID does not exist.
        exceptions.DuplicateOCRJobError: If the document already has an active OCR job.
    """
    logger.info("Submitting OCR job", document_id=document_id)

    with uow:
        _ = uow.documents.get_or_raise(document_id)

        if uow.jobs.has_active_job_for_document(document_id):
            active_job = next(
                j for j in uow.jobs.list_by_document_id(document_id) if j.is_active
            )
            raise DuplicateOCRJobError(document_id=document_id, job_id=active_job.id)

        ocr_job = model.Job(id=generate_id(), document_id=document_id)
        uow.jobs.add(ocr_job)
        uow.commit()

        logger.info("OCR job created", job_id=str(ocr_job.id), document_id=document_id)

        return structs.JobDTO.from_domain(ocr_job)


def start_ocr_job_processing(job_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Marks an OCR job as processing and creates an outbox entry for task scheduling.

    Retrieves the OCR job by its ID, verifies that it exists, and updates its
    status to PROCESSING. Creates an outbox entry for reliable task scheduling.
    Only jobs in PENDING status can be marked as processing.

    Args:
        job_id: The unique identifier of the OCR job to start processing.
        uow: Unit of Work instance.

    Returns:
        The updated JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the OCR job with the given ID does not exist.
        exceptions.InvalidJobStatusTransitionError: If job is not in PENDING status.
    """
    task_id = generate_id()

    with uow:
        ocr_job = uow.jobs.get_or_raise(job_id)
        ocr_job.assign_task_id(task_id)
        ocr_job.update_status(enums.JobStatus.PROCESSING)

        # Create outbox entry for reliable task scheduling
        payload: model.JobProcessingPayload = {"job_id": ocr_job.id}

        outbox_entry = model.OutboxEntry(
            id=generate_id(),
            event_type=enums.OutboxEventType.JOB_SCHEDULING,
            aggregate_id=ocr_job.id,
            payload=payload,
        )
        uow.outbox.add(outbox_entry)
        uow.commit()

        logger.info(
            "OCR job marked as processing with outbox entry",
            job_id=job_id,
            task_id=task_id,
            outbox_entry_id=outbox_entry.id,
        )

        return structs.JobDTO.from_domain(ocr_job)


def complete_ocr_job(
    job_id: str, result_dto: structs.ResultDTO, uow: AbstractUnitOfWork
) -> structs.JobDTO:
    """Completes an OCR job and saves the result.

    Args:
        job_id: The unique identifier of the OCR job.
        result_dto: The processed OCR result DTO.
        uow: Unit of Work instance.

    Returns:
        The updated JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the job is not found.
    """
    ocr_job = uow.jobs.get_or_raise(job_id)

    # Convert DTO back to domain model for persistence
    result = model.Result(
        id=result_dto.id,
        job_id=ocr_job.id,  # Ensure consistency
        content=result_dto.content,
        creation_time=result_dto.creation_time,
    )

    uow.results.add(result)
    ocr_job.update_status(enums.JobStatus.COMPLETED)

    return structs.JobDTO.from_domain(ocr_job)


def fail_ocr_job(
    job_id: str, error_message: str, uow: AbstractUnitOfWork
) -> structs.JobDTO:
    """Marks an OCR job as failed.

    Args:
        job_id: The unique identifier of the OCR job.
        error_message: Description of the error.
        uow: Unit of Work instance.

    Returns:
        The updated JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the job is not found.
    """
    with uow:
        ocr_job = uow.jobs.get_or_raise(job_id)

        ocr_job.update_status(enums.JobStatus.FAILED, error_message=error_message)
        uow.commit()

        return structs.JobDTO.from_domain(ocr_job)


def retry_failed_job(failed_job_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Retries a previously failed OCR job.

    Checks that the original job exists and is in the FAILED status. Creates a
    new OCR job for the same document, allowing the OCR process to be retried
    without affecting the original failed job.

    Args:
        failed_job_id: The unique identifier of the failed OCR job.
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A new JobDTO in PENDING status for retrying the original job.

    Raises:
        exceptions.OCRJobNotFoundError: If the original job does not exist.
        exceptions.InvalidJobStatusTransitionError: If the job is not in FAILED status.
    """
    original_job = uow.jobs.get_or_raise(failed_job_id)

    if original_job.status != enums.JobStatus.FAILED:
        raise exceptions.InvalidJobStatusTransitionError(
            job_id=failed_job_id,
            current=original_job.status,
            attempted=enums.JobStatus.PENDING,
            reason=" Only failed jobs can be retried.",
        )

    new_job = model.Job(id=generate_id(), document_id=original_job.document_id)
    uow.jobs.add(new_job)

    return structs.JobDTO.from_domain(new_job)


def cancel_ocr_job(
    job_id: str, task_runner: TaskRunner, uow: AbstractUnitOfWork
) -> structs.JobDTO:
    """Cancels an OCR job.

    Marks a PENDING or PROCESSING job as failed with a cancellation message.
    COMPLETED and FAILED jobs are returned unchanged.

    Args:
        job_id: The unique identifier of the OCR job.
        task_runner: Task runner for revoking active tasks.
        uow: Unit of Work instance.

    Returns:
        The updated JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the job does not exist.
    """
    with uow:
        ocr_job = uow.jobs.get_or_raise(job_id)

        match ocr_job.status:
            case enums.JobStatus.PENDING:
                ocr_job.update_status(
                    enums.JobStatus.FAILED, error_message="Cancelled by user"
                )

            case enums.JobStatus.PROCESSING:
                # Try to revoke the task if task_id exists
                task_id = ocr_job.task_id
                if task_id:
                    try:
                        task_runner.revoke_task(task_id)
                    except Exception as e:
                        logger.exception(
                            "Failed to revoke task", task_id=task_id, error=str(e)
                        )
                        # Continue with cancellation even if revoke fails

                ocr_job.update_status(
                    enums.JobStatus.FAILED,
                    error_message="Cancelled by user - processing may continue until worker picks up cancellation",
                )

            case _:  # COMPLETED or FAILED
                return structs.JobDTO.from_domain(ocr_job)

        # Additional outbox cleanup: revoke task if outbox entry has been relayed
        task_id = ocr_job.task_id
        if task_id:
            try:
                outbox_entry = uow.outbox.get(task_id)
                if outbox_entry and outbox_entry.is_relayed:
                    task_runner.revoke_task(task_id)
            except Exception as e:
                logger.exception(
                    "Failed to revoke outbox task", task_id=task_id, error=str(e)
                )

        uow.commit()
        return structs.JobDTO.from_domain(ocr_job)


def retry_ocr_job(job_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Retry a failed OCR job by creating a new job for the same document.

    Args:
        job_id: The ID of the failed job to retry.
        uow: Unit of Work instance.

    Returns:
        JobDTO containing the newly created job information.

    Raises:
        exceptions.OCRJobNotFoundError: If the original job does not exist.
        exceptions.InvalidJobStatusTransitionError: If the job is not in FAILED status.
    """
    logger.info("Retrying failed OCR job", job_id=job_id)

    with uow:
        new_job_dto = retry_failed_job(job_id, uow)
        uow.commit()

        logger.info(
            "Created retry job",
            original_job_id=job_id,
            new_job_id=new_job_dto.id,
            document_id=new_job_dto.document_id,
        )

        return new_job_dto


class DuplicateOCRJobError(DomainException):
    code: str = "DUPLICATE_OCR_JOB"

    def __init__(
        self, document_id: str, job_id: str | None = None, message: str | None = None
    ):
        msg = message or (
            f"Document {document_id} already has a pending or active job"
            + (f": {job_id}" if job_id else "")
        )
        super().__init__(message=msg, document_id=document_id, job_id=job_id)
