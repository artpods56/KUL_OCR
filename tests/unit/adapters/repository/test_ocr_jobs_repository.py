from ocr_kul.adapters.database.repository import FakeOcrJobRepository
from ocr_kul.domain import model
from ocr_kul.domain.model import JobStatus
from tests import factories


class TestOcrJobRepository:
    def test_add_and_get_job(
        self, fake_ocr_job_repository: FakeOcrJobRepository, ocr_job: model.OCRJob
    ):
        fake_ocr_job_repository.add(ocr_job)
        retrieved = fake_ocr_job_repository.get(ocr_job.id)

        assert retrieved is not None
        assert retrieved.id == ocr_job.id
        assert retrieved.status == ocr_job.status

    def test_get_nonexistent_job_returns_none(
        self, fake_ocr_job_repository: FakeOcrJobRepository
    ):
        result = fake_ocr_job_repository.get("nonexistent-job-id")

        assert result is None

    def test_add_multiple_jobs(self, fake_ocr_job_repository: FakeOcrJobRepository):
        all_jobs = factories.generate_ocr_jobs()

        for ocr_job in all_jobs:
            fake_ocr_job_repository.add(ocr_job)

        for ocr_job in all_jobs:
            retrieved = fake_ocr_job_repository.get(ocr_job.id)
            assert retrieved is not None
            assert retrieved == ocr_job

    def test_list_all_empty_repository(
        self, fake_ocr_job_repository: FakeOcrJobRepository
    ):
        jobs = fake_ocr_job_repository.list_all()

        assert jobs == []

    def test_list_all_jobs(self, fake_ocr_job_repository: FakeOcrJobRepository):
        all_jobs = factories.generate_ocr_jobs()

        for ocr_job in all_jobs:
            fake_ocr_job_repository.add(ocr_job)

        retrieved_all_jobs = fake_ocr_job_repository.list_all()

        for ocr_job in all_jobs:
            assert ocr_job in retrieved_all_jobs

        assert len(retrieved_all_jobs) == len(all_jobs)

    def test_job_state_persists_in_repository(
        self, fake_ocr_job_repository: FakeOcrJobRepository
    ):
        ocr_job = factories.generate_ocr_job(status=JobStatus.PENDING)
        fake_ocr_job_repository.add(ocr_job)

        # Modify the job
        ocr_job.mark_as_processing()
        ocr_job.complete()

        # Retrieve and verify state persisted
        retrieved = fake_ocr_job_repository.get(ocr_job.id)
        assert retrieved is not None
        assert retrieved.status == JobStatus.COMPLETED
        assert retrieved.started_at is not None
        assert retrieved.completed_at is not None

    def test_overwrite_existing_job(
        self, fake_ocr_job_repository: FakeOcrJobRepository
    ):
        ocr_job_1 = factories.generate_ocr_job(status=JobStatus.PENDING)
        ocr_job_1.mark_as_processing()

        ocr_job_2 = factories.generate_ocr_job(status=JobStatus.PENDING)
        ocr_job_2.id = ocr_job_1.id  # Use same ID to test overwrite

        fake_ocr_job_repository.add(ocr_job_1)
        fake_ocr_job_repository.add(ocr_job_2)

        retrieved = fake_ocr_job_repository.get(ocr_job_1.id)
        assert retrieved is not None
        assert retrieved.status == JobStatus.PENDING
        assert retrieved.started_at is None  # Should be reset since it's the new job
        assert len(fake_ocr_job_repository.list_all()) == 1
