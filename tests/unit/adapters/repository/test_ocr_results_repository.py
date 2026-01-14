from tests.fakes.repositories import FakeOcrResultRepository
from tests import factories


class TestOcrResultRepository:
    def test_add_and_get_result(
        self,
        fake_ocr_result_repository: FakeOcrResultRepository,
    ):
        result = factories.generate_ocr_result()
        fake_ocr_result_repository.add(result)
        retrieved = fake_ocr_result_repository.get(result.id)

        assert retrieved is not None
        assert retrieved.id == result.id
        assert retrieved.job_id == result.job_id
        assert len(retrieved.content) == len(result.content)

    def test_get_nonexistent_result_returns_none(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result = fake_ocr_result_repository.get("nonexistent-result-id")

        assert result is None

    def test_add_multiple_results(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result1 = factories.generate_ocr_result()
        result2 = factories.generate_ocr_result()
        result3 = factories.generate_ocr_result()

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
        result1 = factories.generate_ocr_result()
        result2 = factories.generate_ocr_result()

        fake_ocr_result_repository.add(result1)
        fake_ocr_result_repository.add(result2)

        results = fake_ocr_result_repository.list_all()

        assert len(results) == 2
        assert result1 in results
        assert result2 in results

    def test_result_with_single_page(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result = factories.generate_ocr_result(pages_count=1)

        fake_ocr_result_repository.add(result)
        retrieved = fake_ocr_result_repository.get(result.id)

        assert retrieved is not None
        assert len(retrieved.content) == 1
        assert retrieved.content[0].ref.index == 0

    def test_result_with_multi_page_content(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result = factories.generate_ocr_result(pages_count=3)

        fake_ocr_result_repository.add(result)
        retrieved = fake_ocr_result_repository.get(result.id)

        assert retrieved is not None
        assert len(retrieved.content) == 3
        assert retrieved.content[0].ref.index == 0
        assert retrieved.content[1].ref.index == 1
        assert retrieved.content[2].ref.index == 2

    def test_overwrite_existing_result(
        self, fake_ocr_result_repository: FakeOcrResultRepository
    ):
        result1 = factories.generate_ocr_result()
        result2 = factories.generate_ocr_result()
        result2.id = result1.id  # Use same ID to test overwrite

        fake_ocr_result_repository.add(result1)
        fake_ocr_result_repository.add(result2)

        retrieved = fake_ocr_result_repository.get(result1.id)
        assert retrieved is not None
        assert retrieved.job_id == result2.job_id
        assert len(fake_ocr_result_repository.list_all()) == 1
