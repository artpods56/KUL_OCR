from collections.abc import Iterator, Sequence
from pathlib import Path
from uuid import UUID

from kul_ocr.domain import exceptions, model, ports, structs
from kul_ocr.entrypoints import schemas
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.uow import AbstractUnitOfWork


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
    for the document, and persists its metadata in the database.

    Args:
        file_stream: A file-like object containing the document data.
        file_size: Size of the file in bytes.
        file_type: The type/format of the file (e.g., PDF, PNG).
        storage: Storage system used to save the file.
        uow: Unit of Work instance.

    Returns:
        The created Document domain model.

    Raises:
        exceptions.FileUploadError: If saving the file to storage fails.
        ValueError: If the file extension doesn't match the declared file type.
    """
    file_stream.seek(0)
    actual_filename = getattr(file_stream, "name", None) or ""
    actual_extension = Path(actual_filename).suffix.lower()

    if actual_extension and actual_extension != file_type.dot_extension:
        raise ValueError(
            f"Document extension mismatch: declared as {file_type.dot_extension} "
            f"but got {actual_extension}"
        )

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

            return schemas.DocumentResponse.from_domain(document)

        except exceptions.FileUploadError:
            uow.rollback()
            raise


def _get_document_domain(document_id: str, uow: AbstractUnitOfWork) -> model.Document:
    """Gets a document domain model by its ID.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        The Document domain model.

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    document = uow.documents.get(document_id)
    if document is None:
        raise exceptions.DocumentNotFoundError(
            f"Document with ID {document_id} not found"
        )
    return document


def get_document(
    document_id: str | UUID, uow: AbstractUnitOfWork
) -> schemas.DocumentResponse:
    """Gets a document by its ID.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        The Document domain model.

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        document = uow.documents.get(str(document_id))
        if document is None:
            raise exceptions.DocumentNotFoundError(
                f"Document with ID {document_id} not found"
            )
        return schemas.DocumentResponse.from_domain(document)


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
        document = uow.documents.get(document_id)
        if document is None:
            raise exceptions.DocumentNotFoundError(
                f"Document with ID {document_id} not found"
            )
        return structs.DocumentInput(
            id=document.id, file_path=document.file_path, file_type=document.file_type
        )


# --- OCR Processing Services ---


def process_document(
    doc_input: structs.DocumentInput,
    ocr_engine: ports.OCREngine,
    document_loader: ports.DocumentLoader,
) -> model.Result:
    """Processes a document using the provided OCR engine and loader.

    Orchestrates the loading of document pages and their processing by the
    OCR engine. Returns a Result with ProcessedPage objects.

    Args:
        doc_input: The document data to process (no ORM dependencies).
        ocr_engine: The OCR engine to use for image processing.
        document_loader: The loader to use for extracting images from the document.

    Returns:
        A Result containing processed pages with PagePart data.

    Raises:
        ValueError: If no content could be loaded from the document.
    """
    processed_pages: list[model.ProcessedPage] = []

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
            ref=model.PageRef(document_id=doc_input.id, index=page_input.page_number),
            result=page_part,
        )
        processed_pages.append(processed_page)

    if not processed_pages:
        raise ValueError(f"No content could be loaded from document {doc_input.id}")

    return model.Result(
        id=generate_id(),
        job_id="",
        content=processed_pages,
    )


# --- OCR Jobs Services ---


def get_ocr_job(job_id: str, uow: AbstractUnitOfWork) -> model.Job:
    """Gets an OCR job by its ID.

    Args:
        job_id: The unique identifier of the OCR job.
        uow: Unit of Work instance.

    Returns:
        The Job domain model.

    Raises:
        exceptions.OCRJobNotFoundError: If the job does not exist.
    """
    ocr_job = uow.jobs.get(job_id)
    if ocr_job is None:
        raise exceptions.OCRJobNotFoundError(f"OCR Job {job_id} not found")
    return ocr_job


def get_ocr_jobs_by_status(
    status: model.JobStatus, uow: AbstractUnitOfWork
) -> Sequence[model.Job]:
    """Gets OCR jobs filtered by status.

    Queries the database for all OCR jobs that match the given status. Useful
    for monitoring, reporting, or processing jobs in specific states (e.g.,
    PENDING, COMPLETED, FAILED).

    Args:
        status: The status to filter OCR jobs by.
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A sequence of Job instances matching the given status.
    """
    return uow.jobs.list_by_status(status)


def get_ocr_jobs_by_document_id(
    document_id: str, uow: AbstractUnitOfWork
) -> Sequence[model.Job]:
    """Gets all OCR jobs for a specific document.

    Fetches all OCR jobs linked to the given document ID. Can be used to check
    the processing history or current status of a particular document's OCR tasks.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A sequence of Job instances associated with the specified document.
    """
    return uow.jobs.list_by_document_id(document_id)


def get_ocr_jobs(
    uow: AbstractUnitOfWork,
    status: str | None = None,
    document_id: UUID | None = None,
) -> schemas.JobListResponse:
    """Gets OCR jobs with optional filtering by status and/or document ID.

    Args:
        uow: Unit of Work instance.
        status: Optional status to filter by.
        document_id: Optional document ID to filter by.

    Returns:
        A sequence of Job domain models matching the filters.
    """

    with uow:
        if status:
            if status not in [status.value for status in model.JobStatus]:
                raise exceptions.InvalidJobStatusError(f"Invalid status '{status}'")

            jobs = uow.jobs.list_by_status(model.JobStatus(status))
        else:
            jobs = uow.jobs.list_all()
        if document_id:
            jobs = [
                j for j in jobs if j.document_id == str(document_id)
            ]  # [TODO] this asks for trouble
        return schemas.JobListResponse.from_domain(list(jobs))


def get_terminal_ocr_jobs(uow: AbstractUnitOfWork) -> Sequence[model.Job]:
    """Gets OCR jobs that are in a terminal state.

    Retrieves jobs that have reached a final state (COMPLETED or FAILED).
    Useful for reporting and monitoring.

    Args:
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A sequence of Job instances that have reached a terminal state.
    """
    return uow.jobs.list_terminal_jobs()


def submit_ocr_job(document_id: str, uow: AbstractUnitOfWork) -> schemas.JobResponse:
    """Submits a new OCR processing job for a document.

    Creates a new OCR job in PENDING status for the specified document.

    Args:
        document_id: The unique identifier of the document to process.
        uow: Unit of Work instance.

    Returns:
        The created Job domain model.

    Raises:
        exceptions.DocumentNotFoundError: If the document with the given ID does not exist.
        exceptions.DuplicateOCRJobError: If the document already has an active OCR job.
    """
    with uow:
        document = uow.documents.get(document_id)
        if document is None:
            raise exceptions.DocumentNotFoundError(
                f"Document with ID {document_id} not found"
            )

        existing_jobs = uow.jobs.list_by_document_id(document_id)
        active_jobs = [
            j
            for j in existing_jobs
            if j.status in (model.JobStatus.PENDING, model.JobStatus.PROCESSING)
        ]

        if active_jobs:
            raise exceptions.DuplicateOCRJobError(
                f"Document {document_id} already has a pending or processing OCR job"
            )

        ocr_job = model.Job(id=generate_id(), document_id=document_id)
        uow.jobs.add(ocr_job)
        uow.commit()

        return schemas.JobResponse.from_domain(ocr_job)


def start_ocr_job_processing(
    job_id: UUID, uow: AbstractUnitOfWork
) -> schemas.JobResponse:
    """Marks an OCR job as processing.

    Retrieves the OCR job by its ID, verifies that it exists, and updates its
    status to PROCESSING. Only jobs in PENDING status can be marked as
    processing. This is part of the workflow to track job progress.

    Args:
        job_id: The unique identifier of the OCR job to start processing.
        uow: Unit of Work instance.

    Returns:
        The Job instance with its status updated to PROCESSING.

    Raises:
        exceptions.OCRJobNotFoundError: If the OCR job with the given ID does not exist.
    """
    with uow:
        ocr_job = uow.jobs.get(str(job_id))
        if ocr_job is None:
            raise exceptions.OCRJobNotFoundError(f"OCR Job {job_id} not found")

        ocr_job.mark_as_processing()

        uow.commit()

        return schemas.JobResponse.from_domain(ocr_job)


def complete_ocr_job(
    job_id: str, result: model.Result, uow: AbstractUnitOfWork
) -> model.Job:
    """Completes an OCR job and saves the result.

    Args:
        job_id: The unique identifier of the OCR job.
        result: The processed OCR result with pages.
        uow: Unit of Work instance.

    Returns:
        The updated Job instance.

    Raises:
        exceptions.OCRJobNotFoundError: If the job is not found.
    """
    ocr_job = uow.jobs.get(job_id)
    if ocr_job is None:
        raise exceptions.OCRJobNotFoundError(f"OCR Job {job_id} not found")

    result.job_id = ocr_job.id
    uow.results.add(result)
    ocr_job.complete()

    return ocr_job


def fail_ocr_job(
    job_id: UUID, error_message: str, uow: AbstractUnitOfWork
) -> model.Job:
    """Marks an OCR job as failed.

    Args:
        job_id: The unique identifier of the OCR job.
        error_message: Description of the error.
        uow: Unit of Work instance.

    Returns:
        The updated Job instance.

    Raises:
        exceptions.OCRJobNotFoundError: If the job is not found.
    """
    with uow:
        ocr_job = uow.jobs.get(str(job_id))
        if ocr_job is None:
            raise exceptions.OCRJobNotFoundError(f"OCR Job {job_id} not found")

        ocr_job.fail(error_message)
        uow.commit()

        return ocr_job


def retry_failed_job(failed_job_id: str, uow: AbstractUnitOfWork) -> model.Job:
    """Retries a previously failed OCR job.

    Checks that the original job exists and is in the FAILED status. Creates a
    new OCR job for the same document, allowing the OCR process to be retried
    without affecting the original failed job.

    Args:
        failed_job_id: The unique identifier of the failed OCR job.
        uow: Unit of Work instance (transaction management done by caller).

    Returns:
        A new Job instance in PENDING status for retrying the original job.

    Raises:
        exceptions.OCRJobNotFoundError: If the original job does not exist.
        exceptions.InvalidJobStatusError: If the job is not in FAILED status.
    """
    original_job = uow.jobs.get(failed_job_id)
    if original_job is None:
        raise exceptions.OCRJobNotFoundError(f"OCR Job {failed_job_id} not found")

    if original_job.status != model.JobStatus.FAILED:
        raise exceptions.InvalidJobStatusError(
            f"Cannot retry job {failed_job_id} - job status is {original_job.status}, only failed jobs can be retried",
        )

    # Create new job for the same document
    new_job = model.Job(id=generate_id(), document_id=original_job.document_id)
    uow.jobs.add(new_job)

    return new_job


def get_latest_result_for_document(
    document_id: str, uow: AbstractUnitOfWork
) -> schemas.ResultResponse | None:
    """Gets the most recent successful OCR result for a document.

    Finds the most recently finished job for the given document and returns its result.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        The Result of the latest completed job, or None if no completed jobs exist.

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        # Ensure document exists first
        _ = _get_document_domain(document_id, uow)

        # Get the most recent completed job efficiently
        latest_job = uow.jobs.get_latest_completed_for_document(document_id)

        if not latest_job:
            return None

        # Get the result for this job efficiently
        result = uow.results.get_by_job_id(latest_job.id)

        if not result:
            return None

        return schemas.ResultResponse.from_domain(result)


# --- Document Services ---


def get_document_with_latest_result(
    document_id: str, uow: AbstractUnitOfWork
) -> tuple[model.Document, model.Result | None]:
    """Gets a document along with its latest OCR result, if available.

    Args:
        document_id: The unique identifier of the document.
        uow: Unit of Work instance.

    Returns:
        A tuple containing the Document instance and the latest Result
        (or None if no completed OCR jobs exist).

    Raises:
        exceptions.DocumentNotFoundError: If the document does not exist.
    """
    with uow:
        document = _get_document_domain(document_id, uow)
        latest_job = uow.jobs.get_latest_completed_for_document(document_id)

        latest_result = None
        if latest_job:
            latest_result = uow.results.get_by_job_id(latest_job.id)

        return document, latest_result


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
