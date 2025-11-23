from ocr_kul.adapters.database.repository import FakeOcrResultRepository
from ocr_kul.domain.model import (
    OCRResult,
    SimpleOCRValue,
    SinglePageOcrValue,
    MultiPageOcrValue,
)
from tests import factories


class TestOcrResultRepository:
    def test_add_and_get_result(
        self,
        fake_ocr_result_repository: FakeOcrResultRepository,
        simple_ocr_result: OCRResult[SimpleOCRValue],
    ):
        fake_ocr_result_repository.add(simple_ocr_result)
        retrieved = fake_ocr_result_repository.get(simple_ocr_result.id)

        assert retrieved is not None
        assert retrieved.id == simple_ocr_result.id
        assert retrieved.job_id == simple_ocr_result.job_id
        assert isinstance(retrieved.content, SimpleOCRValue)
        assert retrieved.content.content == simple_ocr_result.content.content

    def test_get_nonexistent_result_returns_none(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result = fake_ocr_result_repository.get("nonexistent-result-id")

        assert result is None

    def test_add_multiple_results(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result1 = factories.generate_ocr_result(value_type=SimpleOCRValue)
        result2 = factories.generate_ocr_result(value_type=SimpleOCRValue)
        result3 = factories.generate_ocr_result(value_type=SimpleOCRValue)

        fake_ocr_result_repository.add(result1)
        fake_ocr_result_repository.add(result2)
        fake_ocr_result_repository.add(result3)

        assert fake_ocr_result_repository.get(result1.id) == result1
        assert fake_ocr_result_repository.get(result2.id) == result2
        assert fake_ocr_result_repository.get(result3.id) == result3

    def test_list_all_empty_repository(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        results = fake_ocr_result_repository.list_all()

        assert results == []

    def test_list_all_results(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result1 = factories.generate_ocr_result(value_type=SimpleOCRValue)
        result2 = factories.generate_ocr_result(value_type=SimpleOCRValue)

        fake_ocr_result_repository.add(result1)
        fake_ocr_result_repository.add(result2)

        results = fake_ocr_result_repository.list_all()

        assert len(results) == 2
        assert result1 in results
        assert result2 in results

    def test_result_with_single_page_content(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result = OCRResult(
            id="result-1",
            job_id="job-1",
            content=SinglePageOcrValue(page_number=1, content="Single page text"),
        )

        fake_ocr_result_repository.add(result)
        retrieved = fake_ocr_result_repository.get("result-1")

        assert retrieved is not None
        assert isinstance(retrieved.content, SinglePageOcrValue)
        assert retrieved.content.content == "Single page text"
        assert retrieved.content.page_number == 1

    def test_result_with_multi_page_content(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        text_units = MultiPageOcrValue(
            content=[
                SinglePageOcrValue(page_number=1, content="Page 1 content"),
                SinglePageOcrValue(page_number=2, content="Page 2 content"),
                SinglePageOcrValue(page_number=3, content="Page 3 content"),
            ]
        )

        result = OCRResult(id="result-1", job_id="job-1", content=text_units)

        fake_ocr_result_repository.add(result)
        retrieved = fake_ocr_result_repository.get("result-1")

        assert retrieved is not None
        assert isinstance(retrieved.content, MultiPageOcrValue)
        assert len(retrieved.content.content) == 3
        assert retrieved.content.content[0].content == "Page 1 content"
        assert retrieved.content.content[0].page_number == 1
        assert retrieved.content.content[1].content == "Page 2 content"
        assert retrieved.content.content[1].page_number == 2
        assert retrieved.content.content[2].content == "Page 3 content"
        assert retrieved.content.content[2].page_number == 3

    def test_overwrite_existing_result(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result1 = factories.generate_ocr_result(value_type=SimpleOCRValue)
        result2 = factories.generate_ocr_result(value_type=SimpleOCRValue)
        result2.id = result1.id  # Use same ID to test overwrite

        fake_ocr_result_repository.add(result1)
        fake_ocr_result_repository.add(result2)

        retrieved = fake_ocr_result_repository.get(result1.id)
        assert retrieved is not None
        assert retrieved.job_id == result2.job_id
        assert isinstance(retrieved.content, SimpleOCRValue)
        assert len(fake_ocr_result_repository.list_all()) == 1
