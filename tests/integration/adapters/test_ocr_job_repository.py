import pytest

from core.domain.model import Document, Job
from core.domain.enums import JobStatus, FileType
from core.utils.misc import generate_id
from core.adapters.database.uow import SqlAlchemyUnitOfWork
from core.adapters.database import repository


@pytest.fixture
def document_id(uow: SqlAlchemyUnitOfWork):
    """Create and persist a test document, return its ID"""
    doc_id = generate_id()
    doc = Document(
        id=doc_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(doc)
        uow.commit()

    return doc_id


def test_can_add_and_retrieve_ocr_job(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test adding an OCR job to the database and retrieving it"""
    job_id = generate_id()
    job = Job(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    with uow:
        uow.jobs.add(job)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        retrieved = uow.jobs.get(job_id)
        assert retrieved is not None
        assert retrieved.id == job_id
        assert retrieved.document_id == document_id
        assert retrieved.status == JobStatus.PENDING


def test_list_by_filters_supports_pagination(
    uow: SqlAlchemyUnitOfWork, document_id: str
):
    jobs = [
        Job(id=generate_id(), document_id=document_id, status=JobStatus.PENDING)
        for _ in range(5)
    ]
    with uow:
        for job in jobs:
            uow.jobs.add(job)
        uow.commit()

    # Fetch first page
    with uow:
        page1 = uow.jobs.list_by_filters(status=JobStatus.PENDING, skip=0, limit=2)
        page2 = uow.jobs.list_by_filters(status=JobStatus.PENDING, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        ids_page1 = {job.id for job in page1}
        ids_page2 = {job.id for job in page2}
        assert ids_page1.isdisjoint(ids_page2)


def test_count_by_filters_returns_total(uow: SqlAlchemyUnitOfWork, document_id: str):
    pending_jobs = [
        Job(id=generate_id(), document_id=document_id, status=JobStatus.PENDING)
        for _ in range(3)
    ]
    completed_jobs = [
        Job(id=generate_id(), document_id=document_id, status=JobStatus.COMPLETED)
        for _ in range(2)
    ]

    with uow:
        for job in pending_jobs + completed_jobs:
            uow.jobs.add(job)
        uow.commit()

    with uow:
        total_pending = uow.jobs.count_by_filters(status=JobStatus.PENDING)
        total_completed = uow.jobs.count_by_filters(status=JobStatus.COMPLETED)
        total_all = uow.jobs.count_by_filters()

        assert total_pending == len(pending_jobs)
        assert total_completed == len(completed_jobs)
        assert total_all == len(pending_jobs) + len(completed_jobs)


def test_get_or_raise_returns_job(uow: SqlAlchemyUnitOfWork, document_id: str):
    job_id = generate_id()
    job = Job(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    with uow:
        uow.jobs.add(job)
        uow.commit()

    with uow:
        retrieved = uow.jobs.get_or_raise(job_id)
        assert retrieved.id == job_id


def test_get_or_raise_raises_when_missing(uow: SqlAlchemyUnitOfWork):
    with uow:
        with pytest.raises(repository.OCRJobNotFoundError):
            uow.jobs.get_or_raise("missing-job")


def test_can_list_all_jobs(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test listing all OCR jobs from the database"""
    job_ids = [generate_id() for _ in range(3)]
    jobs = [
        Job(id=job_ids[i], document_id=document_id, status=JobStatus.PENDING)
        for i in range(3)
    ]

    with uow:
        for job in jobs:
            uow.jobs.add(job)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        all_jobs = uow.jobs.list_all()
        assert len(all_jobs) == 3
        assert {job.id for job in all_jobs} == set(job_ids)


def test_can_list_jobs_by_status(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test listing OCR jobs by status"""
    jobs_data = [
        (JobStatus.PENDING, 3),
        (JobStatus.PROCESSING, 2),
        (JobStatus.COMPLETED, 4),
        (JobStatus.FAILED, 1),
    ]

    all_jobs = []
    for status, count in jobs_data:
        for _ in range(count):
            all_jobs.append(
                Job(id=generate_id(), document_id=document_id, status=status)
            )

    with uow:
        for job in all_jobs:
            uow.jobs.add(job)
        uow.commit()

    # Test each status
    for status, expected_count in jobs_data:
        with uow:
            jobs_by_status = uow.jobs.list_by_status(status)
            assert len(jobs_by_status) == expected_count
            assert all(job.status == status for job in jobs_by_status)


def test_can_list_jobs_by_document_id(uow: SqlAlchemyUnitOfWork):
    """Test listing OCR jobs by document ID"""
    # Create two documents
    doc1_id = generate_id()
    doc2_id = generate_id()

    doc1 = Document(
        id=doc1_id,
        file_path="/path/to/test1.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )
    doc2 = Document(
        id=doc2_id,
        file_path="/path/to/test2.pdf",
        file_type=FileType.PDF,
        file_size_bytes=2048,
    )

    # Create jobs for each document
    jobs_doc1 = [
        Job(id=generate_id(), document_id=doc1_id, status=JobStatus.PENDING)
        for _ in range(3)
    ]
    jobs_doc2 = [
        Job(id=generate_id(), document_id=doc2_id, status=JobStatus.PENDING)
        for _ in range(2)
    ]

    with uow:
        uow.documents.add(doc1)
        uow.documents.add(doc2)
        for job in jobs_doc1 + jobs_doc2:
            uow.jobs.add(job)
        uow.commit()

    # Test filtering by document ID
    with uow:
        jobs_for_doc1 = uow.jobs.list_by_document_id(doc1_id)
        assert len(jobs_for_doc1) == 3
        assert all(job.document_id == doc1_id for job in jobs_for_doc1)

        jobs_for_doc2 = uow.jobs.list_by_document_id(doc2_id)
        assert len(jobs_for_doc2) == 2
        assert all(job.document_id == doc2_id for job in jobs_for_doc2)


def test_can_list_terminal_jobs(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test listing terminal jobs (COMPLETED or FAILED)"""
    jobs = [
        Job(id=generate_id(), document_id=document_id, status=JobStatus.PENDING),
        Job(id=generate_id(), document_id=document_id, status=JobStatus.PROCESSING),
        Job(id=generate_id(), document_id=document_id, status=JobStatus.COMPLETED),
        Job(id=generate_id(), document_id=document_id, status=JobStatus.COMPLETED),
        Job(id=generate_id(), document_id=document_id, status=JobStatus.FAILED),
    ]

    with uow:
        for job in jobs:
            uow.jobs.add(job)
        uow.commit()

    # Retrieve terminal jobs
    with uow:
        terminal_jobs = uow.jobs.list_terminal_jobs()
        assert len(terminal_jobs) == 3  # 2 COMPLETED + 1 FAILED
        assert all(
            job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
            for job in terminal_jobs
        )


def test_has_active_job_for_document(uow: SqlAlchemyUnitOfWork, document_id: str):
    pending_job = Job(
        id=generate_id(), document_id=document_id, status=JobStatus.PENDING
    )
    pending_job_id = pending_job.id
    completed_job = Job(
        id=generate_id(), document_id=document_id, status=JobStatus.COMPLETED
    )

    with uow:
        uow.jobs.add(pending_job)
        uow.jobs.add(completed_job)
        uow.commit()

    with uow:
        assert uow.jobs.has_active_job_for_document(document_id) is True

    # Mark pending job as failed to remove active jobs
    with uow:
        job = uow.jobs.get(pending_job_id)
        assert job is not None
        job.update_status(JobStatus.FAILED)
        uow.commit()

    with uow:
        assert uow.jobs.has_active_job_for_document(document_id) is False


def test_get_returns_none_for_nonexistent_job(uow: SqlAlchemyUnitOfWork):
    """Test that get returns None for a job that doesn't exist"""
    with uow:
        result = uow.jobs.get("nonexistent-id")
        assert result is None


def test_job_status_updates_are_persisted(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test that job status updates are correctly persisted"""
    job_id = generate_id()
    job = Job(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    # Add job
    with uow:
        uow.jobs.add(job)
        uow.commit()

    # Update status to PROCESSING
    with uow:
        retrieved_job = uow.jobs.get(job_id)
        assert retrieved_job is not None
        retrieved_job.update_status(JobStatus.PROCESSING)
        uow.commit()

    # Verify the update persisted
    with uow:
        updated_job = uow.jobs.get(job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.started_at is not None

    # Update status to COMPLETED
    with uow:
        processing_job = uow.jobs.get(job_id)
        assert processing_job is not None
        processing_job.update_status(JobStatus.COMPLETED)
        uow.commit()

    # Verify the completion persisted
    with uow:
        completed_job = uow.jobs.get(job_id)
        assert completed_job is not None
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.completed_at is not None
