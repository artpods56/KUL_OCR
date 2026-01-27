from collections.abc import Iterator, Sequence
from pathlib import Path

from structlog import get_logger

from kul_ocr.domain import exceptions, model, ports, structs
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.uow import AbstractUnitOfWork

logger = get_logger()


# --- Document Services ---


def upload_document(
    file_stream: ports.FileStreamProtocol,
    file_size: int,
    file_type: model.FileType,
    storage: ports.FileStorage,
    uow: AbstractUnitOfWork,
) -> structs.DocumentDTO:
    """Uploads a document to storage and saves it in the database.

    Saves the provided file stream to the storage system, generates a unique ID
    for the document, and persists its metadata in the database.

    Args:
        file_stream: A file-like object containing the document data.
        file_size: Size of the file in bytes.
        file_type: The type/format of the file (e.g., PDF, PNG).
        storage: Storage system used to save the file.
        uow: Unit of Work instance.

    Returns:
        The created DocumentDTO.

    Raises:
        exceptions.FileUploadError: If saving the file to storage fails.
        ValueError: If the file extension doesn't match the declared file type.
    """
    logger.info(
        "Starting document upload", file_type=file_type.value, file_size_bytes=file_size
    )

    file_stream.seek(0)
    actual_filename = getattr(file_stream, "name", None) or ""

    file_type.validate_extension(actual_filename)

    with uow:
        document_uuid = generate_id()
        storage_file_path = Path(document_uuid + file_type.dot_extension)

        document = model.Document(
            id=document_uuid,
            file_path=str(storage_file_path),
            file_type=file_type,
            file_size_bytes=file_size,
        )

        try:
            uow.documents.add(document)
            storage.save(stream=file_stream, file_path=storage_file_path)
            uow.commit()

            logger.info(
                "Document uploaded successfully",
                document_id=str(document.id),
                file_path=str(storage_file_path),
            )

            return structs.DocumentDTO.from_domain(document)

        except exceptions.FileUploadError as e:
            logger.error(
                "Document upload failed",
                document_id=document_uuid,
                error=str(e),
                exc_info=True,
            )
            uow.rollback()
            raise


def get_document(document_id: str, uow: AbstractUnitOfWork) -> structs.DocumentDTO:
    """Gets a document by its ID.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        The DocumentDTO containing essential document metadata.

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        document = uow.documents.get_or_raise(document_id)
        return structs.DocumentDTO.from_domain(document)


def get_document_for_processing(
    document_id: str, uow: AbstractUnitOfWork
) -> structs.DocumentInput:
    """Gets a document for OCR processing as a plain data structure.

    Extracts document data from the ORM before the session closes, avoiding
    detached instance errors. Returns a simple dataclass without ORM dependencies.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        A DocumentInput containing the essential document data.

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        document = uow.documents.get_or_raise(document_id)
        return structs.DocumentInput(
            id=document.id, file_path=document.file_path, file_type=document.file_type
        )


# --- OCR Processing Services ---


def process_document(
    doc_input: structs.DocumentInput,
    ocr_engine: ports.OCREngine,
    document_loader: ports.DocumentLoader,
) -> structs.ResultDTO:
    """Processes a document using the provided OCR engine and loader.

    Orchestrates the loading of document pages and their processing by the
    OCR engine. Returns a ResultDTO with ProcessedPage objects.

    Args:
        doc_input: The document data to process (no ORM dependencies).
        ocr_engine: The OCR engine to use for image processing.
        document_loader: The loader to use for extracting images from the document.

    Returns:
        A ResultDTO containing processed pages with PagePart data.

    Raises:
        ValueError: If no content could be loaded from the document.
    """
    logger.info("Starting OCR processing", document_id=str(doc_input.id))

    processed_pages: list[model.ProcessedPage] = []

    try:
        for page_input in document_loader.load_pages(doc_input):
            raw_text = ocr_engine.process_image(page_input.image)
            width, height = page_input.image.size

            page_part = model.wrap_text_in_page_part(
                text=raw_text,
                page_number=page_input.page_number,
                width=width,
                height=height,
            )

            processed_page = model.ProcessedPage(
                ref=model.PageRef(
                    document_id=doc_input.id, index=page_input.page_number
                ),
                result=page_part,
            )
            processed_pages.append(processed_page)

        if not processed_pages:
            raise ValueError(f"No content could be loaded from document {doc_input.id}")

        result = model.Result(
            id=generate_id(),
            job_id="",
            content=processed_pages,
        )

        logger.info(
            "OCR processing completed",
            document_id=str(doc_input.id),
            pages_processed=len(result.content),
        )

        return structs.ResultDTO.from_domain(result)

    except Exception as e:
        logger.error(
            "OCR processing failed",
            document_id=str(doc_input.id),
            error=str(e),
            exc_info=True,
        )
        raise


# --- OCR Jobs Services ---


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
    job = uow.jobs.get_or_raise(job_id)
    return structs.JobDTO.from_domain(job)


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
        ocr_job = uow.jobs.get_or_raise(job_id)
        return structs.JobDTO.from_domain(ocr_job)


def get_ocr_jobs_by_status(
    status: model.JobStatus, uow: AbstractUnitOfWork
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
) -> Sequence[structs.JobDTO]:
    """Gets OCR jobs with optional filtering by status and/or document ID.

    Args:
        uow: Unit of Work instance.
        status: Optional status to filter by.
        document_id: Optional document ID to filter by.

    Returns:
        A sequence of JobDTO matching the filters.
    """
    with uow:
        if status:
            if status not in [s.value for s in model.JobStatus]:
                raise exceptions.UnknownJobStatusError(status=status)

        job_status = model.JobStatus(status) if status else None
        jobs = uow.jobs.list_by_filters(status=job_status, document_id=document_id)
        return [structs.JobDTO.from_domain(job) for job in jobs]


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
                current_status=job.status.value,
                attempted_status="terminal (completed/failed)",
                message=f"Cannot delete job {job_id} - job is in {job.status.value} state. Only terminal jobs (completed, failed) can be deleted.",
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
            raise exceptions.DuplicateOCRJobError(
                document_id=document_id, job_id=active_job.id
            )

        ocr_job = model.Job(id=generate_id(), document_id=document_id)
        uow.jobs.add(ocr_job)
        uow.commit()

        logger.info("OCR job created", job_id=str(ocr_job.id), document_id=document_id)

        return structs.JobDTO.from_domain(ocr_job)


def start_ocr_job_processing(job_id: str, uow: AbstractUnitOfWork) -> structs.JobDTO:
    """Marks an OCR job as processing.

    Retrieves the OCR job by its ID, verifies that it exists, and updates its
    status to PROCESSING. Only jobs in PENDING status can be marked as
    processing. This is part of the workflow to track job progress.

    Args:
        job_id: The unique identifier of the OCR job to start processing.
        uow: Unit of Work instance.

    Returns:
        The updated JobDTO.

    Raises:
        exceptions.OCRJobNotFoundError: If the OCR job with the given ID does not exist.
    """
    with uow:
        ocr_job = uow.jobs.get_or_raise(job_id)
        ocr_job.mark_as_processing()
        uow.commit()
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
    ocr_job.complete()

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

        ocr_job.fail(error_message)
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

    if original_job.status != model.JobStatus.FAILED:
        raise exceptions.InvalidJobStatusTransitionError(
            job_id=failed_job_id,
            current_status=original_job.status.value,
            attempted_status=model.JobStatus.PENDING.value,
        )

    # Create new job for the same document
    new_job = model.Job(id=generate_id(), document_id=original_job.document_id)
    uow.jobs.add(new_job)

    return structs.JobDTO.from_domain(new_job)


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


def get_latest_result_for_document(
    document_id: str, uow: AbstractUnitOfWork
) -> structs.ResultDTO | None:
    """Gets the most recent successful OCR result for a document.

    Finds the most recently finished job for the given document and returns its result.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        The ResultDTO of the latest completed job, or None if no completed jobs exist.

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        _ = uow.documents.get_or_raise(document_id)

        latest_job = uow.jobs.get_latest_completed_for_document(document_id)

        if not latest_job:
            return None

        result = uow.results.get_by_job_id(latest_job.id)

        if not result:
            return None

        return structs.ResultDTO.from_domain(result)


# --- Document Services ---


def get_document_with_latest_result(
    document_id: str, uow: AbstractUnitOfWork
) -> tuple[structs.DocumentDTO, structs.ResultDTO | None]:
    """Gets a document along with its latest OCR result, if available.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        A tuple containing the DocumentDTO and the latest ResultDTO
        (or None if no completed OCR jobs exist).

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        document = uow.documents.get_or_raise(document_id)
        latest_job = uow.jobs.get_latest_completed_for_document(document_id)

        latest_result_dto = None
        if latest_job:
            latest_result = uow.results.get_by_job_id(latest_job.id)
            if latest_result:
                latest_result_dto = structs.ResultDTO.from_domain(latest_result)

        return structs.DocumentDTO.from_domain(document), latest_result_dto


def download_document(
    document_id: str, storage: ports.FileStorage, uow: AbstractUnitOfWork
) -> tuple[Iterator[bytes], str, str] | None:
    """Downloads a document as a streaming response.

    Args:
        document_id: The unique identifier of the document.
        storage: File storage implementation.
        uow: Unit of Work instance.

    Returns:
        Tuple of (stream_generator, content_type, filename) or None if not found.
    """
    with uow:
        document = uow.documents.get(document_id)
        if not document:
            return None

        file_path = Path(document.file_path)
        filename = f"{document.id}{document.file_type.dot_extension}"
        content_type = document.file_type.value

        def stream_chunks() -> Iterator[bytes]:
            CHUNK_SIZE = 65536  # 64KB
            with storage.load(file_path) as file_stream:
                while chunk := file_stream.read(CHUNK_SIZE):
                    yield chunk

        return stream_chunks(), content_type, filename
