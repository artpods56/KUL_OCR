import pytest

from ocr_kul.domain.model import Document, FileType, OCRJob, JobStatus
from ocr_kul.service_layer.services import generate_id
from ocr_kul.service_layer.uow import SqlAlchemyUnitOfWork


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
    job = OCRJob(id=job_id, document_id=document_id, status=JobStatus.PENDING)

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


def test_can_list_all_jobs(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test listing all OCR jobs from the database"""
    job_ids = [generate_id() for _ in range(3)]
    jobs = [
        OCRJob(id=job_ids[i], document_id=document_id, status=JobStatus.PENDING)
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
                OCRJob(id=generate_id(), document_id=document_id, status=status)
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
        OCRJob(id=generate_id(), document_id=doc1_id, status=JobStatus.PENDING)
        for _ in range(3)
    ]
    jobs_doc2 = [
        OCRJob(id=generate_id(), document_id=doc2_id, status=JobStatus.PENDING)
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
        OCRJob(id=generate_id(), document_id=document_id, status=JobStatus.PENDING),
        OCRJob(id=generate_id(), document_id=document_id, status=JobStatus.PROCESSING),
        OCRJob(id=generate_id(), document_id=document_id, status=JobStatus.COMPLETED),
        OCRJob(id=generate_id(), document_id=document_id, status=JobStatus.COMPLETED),
        OCRJob(id=generate_id(), document_id=document_id, status=JobStatus.FAILED),
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


def test_get_returns_none_for_nonexistent_job(uow: SqlAlchemyUnitOfWork):
    """Test that get returns None for a job that doesn't exist"""
    with uow:
        result = uow.jobs.get("nonexistent-id")
        assert result is None


def test_job_status_updates_are_persisted(uow: SqlAlchemyUnitOfWork, document_id: str):
    """Test that job status updates are correctly persisted"""
    job_id = generate_id()
    job = OCRJob(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    # Add job
    with uow:
        uow.jobs.add(job)
        uow.commit()

    # Update status to PROCESSING
    with uow:
        retrieved_job = uow.jobs.get(job_id)
        assert retrieved_job is not None
        retrieved_job.mark_as_processing()
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
        processing_job.complete()
        uow.commit()

    # Verify the completion persisted
    with uow:
        completed_job = uow.jobs.get(job_id)
        assert completed_job is not None
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.completed_at is not None
