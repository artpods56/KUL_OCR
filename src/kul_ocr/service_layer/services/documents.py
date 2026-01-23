from pathlib import Path
from typing import Sequence

import kul_ocr.adapters.storages.local
from kul_ocr.domain import ports, model, structs, exceptions
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.parsing import (
    MIN_MAGIC_BYTES,
    validate_file_content,
    sanitize_filename,
)
from kul_ocr.service_layer.uow import AbstractUnitOfWork

from kul_ocr.utils.logger import get_logger

logger = get_logger(__name__)


def upload_document(
    file_stream: ports.FileStreamProtocol,
    file_size: int,
    file_type: model.FileType,
    storage: ports.FileStorage,
    uow: AbstractUnitOfWork,
    original_filename: str | None = None,
    max_bytes: int | None = None,
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
        original_filename: The original filename from the client upload (optional).
        max_bytes: Optional maximum file size in bytes for validation.

    Returns:
        The created DocumentDTO.

    Raises:
        exceptions.FileUploadError: If saving the file to storage fails.
        ValueError: If the file extension doesn't match the declared file type.
        FileSizeExceededError: If file exceeds max_bytes limit.
    """
    logger.info(
        "Starting document upload", file_type=file_type.value, file_size_bytes=file_size
    )

    if max_bytes is not None and file_size > max_bytes:
        raise exceptions.FileSizeExceededError(
            file_size=file_size,
            max_bytes=max_bytes,
        )

    header_bytes = file_stream.read(MIN_MAGIC_BYTES)
    _ = file_stream.seek(0)
    validate_file_content(header_bytes, file_type)

    file_type.validate_extension(
        original_filename or ("unknown" + file_type.dot_extension)
    )

    sanitized_filename = sanitize_filename(original_filename)

    with uow:
        document_uuid = generate_id()
        storage_file_path = Path(document_uuid + file_type.dot_extension)

        document = model.Document(
            id=document_uuid,
            file_path=str(storage_file_path),
            file_type=file_type,
            file_size_bytes=file_size,
            original_filename=sanitized_filename,
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

        except kul_ocr.adapters.storages.local.FileUploadError as e:
            logger.error(
                "Document upload failed",
                document_id=document_uuid,
                error=str(e),
                exc_info=True,
            )
            uow.rollback()
            raise


def get_documents(uow: AbstractUnitOfWork) -> Sequence[structs.DocumentDTO]:
    """Gets all documents.

    Args:
        uow: Unit of Work instance.

    Returns:
        A sequence of DocumentDTOs.
    """
    with uow:
        documents = uow.documents.list_all()
        return [structs.DocumentDTO.from_domain(doc) for doc in documents]


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
