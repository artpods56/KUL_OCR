from pathlib import Path
from typing import Sequence, Iterator

from core.domain import ports, enums, model
from core.utils.misc import generate_id
from backend.documents.parsing import (
    MIN_MAGIC_BYTES,
    get_mime_from_bytes,
    sanitize_filename,
)
from core.domain.ports import AbstractUnitOfWork
from core.utils.logger import get_logger

from . import dto, validator

logger = get_logger(__name__)


def validate_uploaded_file(
    file_stream: ports.FileStreamProtocol,
    file_size: int,
    file_type: enums.FileType,
    max_bytes: int,
    file_name: str | None = None,
) -> None:
    validator.validate_file_size(file_size, max_bytes)

    if file_name:
        validator.validate_file_extension(file_type, file_name)

    header_bytes = file_stream.read(MIN_MAGIC_BYTES)
    _ = file_stream.seek(0)
    uploaded_mime = get_mime_from_bytes(header_bytes)

    validator.validate_mime_type(file_type, uploaded_mime)


def prepare_document(
    file_name: str, file_type: enums.FileType, file_size: int
) -> model.Document:
    return model.Document(
        file_type=file_type,
        file_size_bytes=file_size,
        original_filename=sanitize_filename(file_name),
    )


def upload_document(
    file_stream: ports.FileStreamProtocol,
    document: model.Document,
    staging_file_path: Path,
    uploaded_file_path: Path,
    storage: ports.FileStorage,
    uow: AbstractUnitOfWork,
) -> dto.DocumentDTO:
    storage.save(file_stream, staging_file_path)

    with uow:
        uow.documents.add(document)

        payload: model.DocumentUploadPayload = {
            "document_id": document.id,
            "staging_file_path": str(staging_file_path),
            "uploaded_file_path": str(uploaded_file_path),
        }

        uow.outbox.add(
            model.OutboxEntry(
                event_type=enums.OutboxEventType.DOCUMENT_UPLOAD,
                aggregate_id=document.id,
                payload=payload,
            )
        )
        uow.commit()

        return dto.DocumentDTO.from_domain(document)


def get_documents(uow: AbstractUnitOfWork) -> Sequence[dto.DocumentDTO]:
    """Gets all documents.

    Args:
        uow: Unit of Work instance.

    Returns:
        A sequence of DocumentDTOs.
    """
    with uow:
        documents = uow.documents.list_all()
        return [dto.DocumentDTO.from_domain(doc) for doc in documents]


def get_document(document_id: str, uow: AbstractUnitOfWork) -> dto.DocumentDTO:
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
        return dto.DocumentDTO.from_domain(document)


def get_document_for_processing(
    document_id: str, uow: AbstractUnitOfWork
) -> model.DocumentInput:
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
        return model.DocumentInput(
            id=document.id,
            file_path=document.file_path or "unknown",
            file_type=document.file_type,
        )


def process_document(
    doc_input: model.DocumentInput,
    ocr_engine: ports.OCREngine,
    document_loader: ports.DocumentLoader,
) -> dto.ResultDTO:
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

        return dto.ResultDTO.from_domain(result)

    except Exception as e:
        logger.error(
            "OCR processing failed",
            document_id=str(doc_input.id),
            error=str(e),
            exc_info=True,
        )
        raise


def get_document_with_latest_result(
    document_id: str, uow: AbstractUnitOfWork
) -> tuple[dto.DocumentDTO, dto.ResultDTO | None]:
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
                latest_result_dto = dto.ResultDTO.from_domain(latest_result)

        return dto.DocumentDTO.from_domain(document), latest_result_dto


def get_latest_result_for_document(
    document_id: str, uow: AbstractUnitOfWork
) -> dto.ResultDTO | None:
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

        return dto.ResultDTO.from_domain(result)


def download_document(
    document_id: str, storage: ports.FileStorage, uow: AbstractUnitOfWork
) -> tuple[Iterator[bytes], str, str]:
    """Downloads a document as a streaming response.

    Args:
        document_id: The unique identifier of the document.
        storage: File storage implementation.
        uow: Unit of Work instance.

    Returns:
        Tuple of (stream_generator, content_type, filename) or None if not found.
    """
    with uow:
        document = uow.documents.get_or_raise(document_id)

        file_path = Path(document.file_path)
        display_name = document.display_name
        content_type = document.file_type.value

        def stream_chunks() -> Iterator[bytes]:
            CHUNK_SIZE = 65536  # 64KB
            with storage.load(file_path) as file_stream:
                while chunk := file_stream.read(CHUNK_SIZE):
                    yield chunk

        return stream_chunks(), content_type, display_name
