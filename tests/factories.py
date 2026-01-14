import random
import uuid
from collections.abc import Sequence
from pathlib import Path

from kul_ocr.domain import model
from kul_ocr.service_layer.helpers import generate_id


# --- OCR Jobs Factories ---


def generate_ocr_job(
    status: model.JobStatus | None = model.JobStatus.PENDING,
    document_id: str | None = None,
) -> model.Job:
    job_status = status or random.choice(list(model.JobStatus))

    return model.Job(
        id=generate_id(),
        document_id=document_id or generate_id(),
        status=job_status,
    )


def generate_ocr_jobs(
    jobs_count: int = 10, status: model.JobStatus | None = None
) -> Sequence[model.Job]:
    return [generate_ocr_job(status=status) for _ in range(jobs_count)]


def generate_document(
    dir_path: Path, file_type: model.FileType | None = None, file_size_in_bytes: int = 0
) -> model.Document:
    file_type = file_type or random.choice(list(model.FileType))
    document_id = generate_id()
    document_path = Path(dir_path / document_id).with_suffix(file_type.dot_extension)

    return model.Document(
        id=generate_id(),
        file_path=str(document_path),
        file_type=file_type,
        file_size_bytes=file_size_in_bytes,
    )


def generate_documents(
    dir_path: Path, documents_count: int = 10, file_type: model.FileType | None = None
) -> Sequence[model.Document]:
    return [
        generate_document(
            dir_path=dir_path / generate_id(),
            file_type=file_type or random.choice(list(model.FileType)),
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
