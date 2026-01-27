import random
import uuid
from collections.abc import Sequence
from pathlib import Path

from kul_ocr.domain import model, enums
from kul_ocr.service_layer.helpers import generate_id


# --- OCR Jobs Factories ---


def generate_ocr_job(
    status: enums.JobStatus | None = enums.JobStatus.PENDING,
    document_id: str | None = None,
) -> model.Job:
    job_status = status or random.choice(list(enums.JobStatus))

    return model.Job(
        id=generate_id(),
        document_id=document_id or generate_id(),
        status=job_status,
    )


def generate_ocr_jobs(
    jobs_count: int = 10, status: enums.JobStatus | None = None
) -> Sequence[model.Job]:
    return [generate_ocr_job(status=status) for _ in range(jobs_count)]


def generate_document(
    dir_path: Path,
    file_type: enums.FileType | None = None,
    file_size_in_bytes: int = 0,
    original_filename: str | None = None,
) -> model.Document:
    file_type = file_type or random.choice(list(enums.FileType))
    document_id = generate_id()
    document_path = Path(dir_path / document_id).with_suffix(file_type.dot_extension)

    return model.Document(
        original_filename=original_filename or f"test_document{file_type.dot_extension}",
        file_type=file_type,
        file_path=str(document_path),
        file_size_bytes=file_size_in_bytes,
    )


def generate_document_without_file(
    file_type: enums.FileType | None = None,
    file_size_in_bytes: int = 0,
    original_filename: str | None = None,
) -> model.Document:
    """Generate a document entity without requiring an actual file on disk.

    Useful for database integration tests where the file storage is not being tested.
    """
    file_type = file_type or random.choice(list(enums.FileType))
    document_id = generate_id()

    return model.Document(
        original_filename=original_filename or f"test_document{file_type.dot_extension}",
        file_type=file_type,
        file_path=f"/fake/path/{document_id}{file_type.dot_extension}",
        file_size_bytes=file_size_in_bytes,
    )


def generate_documents(
    dir_path: Path, documents_count: int = 10, file_type: enums.FileType | None = None
) -> Sequence[model.Document]:
    return [
        generate_document(
            dir_path=dir_path / generate_id(),
            file_type=file_type or random.choice(list(enums.FileType)),
        )
        for _ in range(documents_count)
    ]


# --- OCR Results Factories ---


def generate_text_part(text: str | None = None) -> model.TextPart:
    return model.TextPart(
        text=text or str(uuid.uuid4()),
        bbox=model.BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=100.0),
        confidence=random.uniform(0.5, 1.0),
        level=random.choice(["word", "line", "block"]),
    )


def generate_page_part(
    page_number: int | None = None, width: int = 1000, height: int = 1200
) -> model.PagePart:
    parts_count = random.randint(1, 10)
    parts = [generate_text_part() for _ in range(parts_count)]

    return model.PagePart(
        parts=parts,
        metadata=model.PageMetadata(
            page_number=page_number or random.randint(1, 10),
            width=width,
            height=height,
        ),
    )


def generate_processed_page(
    document_id: str | None = None, index: int | None = None
) -> model.ProcessedPage:
    page_part = generate_page_part(page_number=index)

    return model.ProcessedPage(
        ref=model.PageRef(
            document_id=document_id or generate_id(),
            index=index or 0,
        ),
        result=page_part,
    )


def generate_ocr_result(
    document_id: str | None = None, pages_count: int | None = None
) -> model.Result:
    if pages_count is None:
        pages_count = random.randint(1, 10)

    doc_id = document_id or generate_id()

    content = [
        generate_processed_page(document_id=doc_id, index=i) for i in range(pages_count)
    ]

    result = model.Result(
        id=generate_id(),
        job_id=generate_id(),
        content=content,
    )

    return result


def generate_ocr_results(
    results_count: int = 10,
) -> Sequence[model.Result]:
    """Generate multiple OCR results."""
    return [generate_ocr_result() for _ in range(results_count)]


# --- Outbox Entry Factories ---


def generate_outbox_entry(
    event_type: enums.OutboxEventType = enums.OutboxEventType.JOB_SCHEDULING,
    aggregate_id: str | None = None,
    payload: model.OutboxPayload | None = None,
) -> model.OutboxEntry:
    """Generate an outbox entry for testing."""
    agg_id = aggregate_id or generate_id()

    if payload is None:
        if event_type == enums.OutboxEventType.JOB_SCHEDULING:
            payload = model.JobProcessingPayload(
                job_id=agg_id,
                task_id=generate_id(),
                document_id=generate_id(),
            )
        else:  # DOCUMENT_UPLOAD
            payload = model.DocumentUploadPayload(
                document_id=agg_id,
                staging_file_path=f"/staging/{agg_id}",
                uploaded_file_path=f"/uploaded/{agg_id}",
            )

    return model.OutboxEntry(
        id=generate_id(),
        event_type=event_type,
        aggregate_id=agg_id,
        payload=payload,
    )


def generate_outbox_entries(
    count: int = 5,
    event_type: enums.OutboxEventType = enums.OutboxEventType.JOB_SCHEDULING,
) -> Sequence[model.OutboxEntry]:
    """Generate multiple outbox entries for testing."""
    return [generate_outbox_entry(event_type=event_type) for _ in range(count)]
