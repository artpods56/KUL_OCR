from pathlib import Path

import pytest

from tests.fakes.repositories import (
    FakeDocumentRepository,
    FakeOcrJobRepository,
    FakeOcrResultRepository,
)
from tests.fakes.uow import FakeUnitOfWork
from tests import factories


@pytest.fixture
def uow():
    return FakeUnitOfWork()


@pytest.fixture
def ocr_job():
    return factories.generate_ocr_job()


@pytest.fixture
def document(tmp_path: Path):
    return factories.generate_document(dir_path=tmp_path)


@pytest.fixture
def fake_doc_repo() -> FakeDocumentRepository:
    return FakeDocumentRepository()


@pytest.fixture
def fake_ocr_job_repository() -> FakeOcrJobRepository:
    return FakeOcrJobRepository()


@pytest.fixture
def fake_ocr_result_repository() -> FakeOcrResultRepository:
    return FakeOcrResultRepository()


@pytest.fixture
def simple_ocr_result():
    """OCR result with SimpleOCRValue content."""
    from kul_ocr.domain.model import SimpleOCRValue

    return factories.generate_ocr_result(value_type=SimpleOCRValue)


@pytest.fixture
def single_page_ocr_result():
    """OCR result with SinglePageOcrValue content."""
    from kul_ocr.domain.model import SinglePageOcrValue

    return factories.generate_ocr_result(value_type=SinglePageOcrValue)


@pytest.fixture
def multi_page_ocr_result():
    """OCR result with MultiPageOcrValue content."""
    from kul_ocr.domain.model import MultiPageOcrValue

    return factories.generate_ocr_result(value_type=MultiPageOcrValue)
