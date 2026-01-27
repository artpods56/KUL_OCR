from pathlib import Path
from collections.abc import Iterator

from kul_ocr.domain import structs, ports
from kul_ocr.service_layer.uow import AbstractUnitOfWork

from kul_ocr.utils.logger import get_logger

logger = get_logger(__name__)


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
