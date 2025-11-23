import random
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, overload

from ocr_kul.domain import model
from ocr_kul.domain.model import BaseOCRValue, OCRValueTypes, OCRResult
from ocr_kul.service_layer.services import generate_id


# --- OCR Jobs Factories ---


def generate_ocr_job(
    status: model.JobStatus | None = model.JobStatus.PENDING,
) -> model.OCRJob:
    job_status = status or random.choice(list(model.JobStatus))

    return model.OCRJob(
        id=generate_id(),
        document_id=generate_id(),
        status=job_status,
    )


def generate_ocr_jobs(
    jobs_count: int = 10, status: model.JobStatus | None = None
) -> Sequence[model.OCRJob]:
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


# --- OCR Value Factories ---


def _generate_simple_ocr_result() -> model.SimpleOCRValue:
    return model.SimpleOCRValue(
        content=str(uuid.uuid4()),
    )


def _generate_single_page_ocr_result() -> model.SinglePageOcrValue:
    return model.SinglePageOcrValue(
        page_number=random.randint(1, 100),
        content=str(uuid.uuid4()),
    )


def _generate_multi_page_ocr_result() -> model.MultiPageOcrValue:
    return model.MultiPageOcrValue(
        content=[
            _generate_single_page_ocr_result() for _ in range(random.randint(1, 10))
        ],
    )


_OCR_RESULTS_FACTORY_MAP: dict[
    type[model.BaseOCRValue[Any]], Callable[[], model.BaseOCRValue[Any]]
] = {
    model.SimpleOCRValue: _generate_simple_ocr_result,
    model.SinglePageOcrValue: _generate_single_page_ocr_result,
    model.MultiPageOcrValue: _generate_multi_page_ocr_result,
}


@overload
def ocr_value_factory(
    value_type: type[model.SimpleOCRValue],
) -> model.SimpleOCRValue: ...


@overload
def ocr_value_factory(
    value_type: type[model.SinglePageOcrValue],
) -> model.SinglePageOcrValue: ...


@overload
def ocr_value_factory(
    value_type: type[model.MultiPageOcrValue],
) -> model.MultiPageOcrValue: ...


@overload
def ocr_value_factory[ValueT: BaseOCRValue[Any]](
    value_type: type[ValueT],
) -> ValueT: ...


def ocr_value_factory(
    value_type: type[BaseOCRValue[Any]],
) -> model.BaseOCRValue[Any]:
    try:
        factory_func = _OCR_RESULTS_FACTORY_MAP[value_type]
    except KeyError:
        raise ValueError(
            f"Unknown value type for OCR Results factory: {value_type}"
        ) from None

    result = factory_func()

    # mypy/runtime safety net
    if not isinstance(result, value_type):
        raise TypeError(
            f"Factory for {value_type.__name__} returned wrong type: {type(result).__name__}"
        )

    return result


# --- OCR Results Factories ---


def generate_ocr_result[ValueT: OCRValueTypes](
    value_type: type[ValueT],
    job_id: str | None = None,
) -> OCRResult[ValueT]:
    """Generate single OCR result for given value_type."""
    return model.OCRResult(
        id=generate_id(),
        job_id=job_id or generate_id(),
        content=ocr_value_factory(value_type=value_type),
    )


def generate_ocr_results[ValueT: OCRValueTypes](
    value_type: type[ValueT],
    results_count: int = 10,
) -> Sequence[OCRResult[ValueT]]:
    """Generate multiple OCR results for given value_type."""
    return [generate_ocr_result(value_type=value_type) for _ in range(results_count)]
