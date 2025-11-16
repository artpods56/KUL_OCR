from ocr_kul.domain.model import (
    Document,
    FileType,
    OCRJob,
    JobStatus,
    OCRResult,
    SimpleOCRValue,
)
from ocr_kul.service_layer.services import generate_id
from ocr_kul.service_layer.uow import SqlAlchemyUnitOfWork


def test_uow_can_commit_changes(uow: SqlAlchemyUnitOfWork):
    """Test that Unit of Work commits changes to the database"""
    document_id = generate_id()
    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(document)
        uow.commit()

    # Verify in a new transaction that the document was persisted
    with uow:
        retrieved = uow.documents.get(document_id)
        assert retrieved is not None
        assert retrieved.id == document_id


def test_uow_rolls_back_on_error(uow: SqlAlchemyUnitOfWork):
    """Test that Unit of Work rolls back changes when an error occurs"""
    document_id = generate_id()
    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    try:
        with uow:
            uow.documents.add(document)
            # Simulate an error before commit
            raise Exception("Simulated error")
    except Exception:
        pass  # Expected

    # Verify the document was NOT persisted due to rollback
    with uow:
        retrieved = uow.documents.get(document_id)
        assert retrieved is None


def test_uow_rolls_back_uncommitted_changes(uow: SqlAlchemyUnitOfWork):
    """Test that Unit of Work rolls back changes if commit is not called"""
    document_id = generate_id()
    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(document)
        # Exit without calling commit

    # Verify the document was NOT persisted
    with uow:
        retrieved = uow.documents.get(document_id)
        assert retrieved is None


def test_uow_handles_multiple_operations_in_transaction(uow: SqlAlchemyUnitOfWork):
    """Test that Unit of Work handles multiple operations in a single transaction"""
    document_id = generate_id()
    job_id = generate_id()
    result_id = generate_id()

    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    job = OCRJob(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    result = OCRResult(
        id=result_id, job_id=job_id, content=SimpleOCRValue(content="OCR text content")
    )

    with uow:
        uow.documents.add(document)
        uow.jobs.add(job)
        uow.results.add(result)
        uow.commit()

    # Verify all entities were persisted
    with uow:
        retrieved_doc = uow.documents.get(document_id)
        retrieved_job = uow.jobs.get(job_id)
        retrieved_result = uow.results.get(result_id)

        assert retrieved_doc is not None
        assert retrieved_job is not None
        assert retrieved_result is not None
        assert retrieved_job.document_id == document_id
        assert retrieved_result.job_id == job_id


def test_uow_atomic_transaction_all_or_nothing(uow: SqlAlchemyUnitOfWork):
    """Test that Unit of Work transactions are atomic (all or nothing)"""
    # First, create a valid document
    existing_doc_id = generate_id()
    existing_doc = Document(
        id=existing_doc_id,
        file_path="/path/to/existing.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(existing_doc)
        uow.commit()

    # Now try to add a new document and job, but cause an error
    new_document_id = generate_id()
    new_document = Document(
        id=new_document_id,
        file_path="/path/to/new.pdf",
        file_type=FileType.PDF,
        file_size_bytes=2048,
    )

    try:
        with uow:
            uow.documents.add(new_document)
            # This should succeed

            # Now raise an error before commit
            raise ValueError("Transaction should roll back")
    except ValueError:
        pass  # Expected

    # Verify the existing document is still there
    # but the new document was NOT persisted
    with uow:
        existing = uow.documents.get(existing_doc_id)
        new = uow.documents.get(new_document_id)

        assert existing is not None
        assert new is None


def test_uow_updates_are_persisted(uow: SqlAlchemyUnitOfWork):
    """Test that updates to entities are persisted correctly"""
    document_id = generate_id()
    job_id = generate_id()

    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    job = OCRJob(id=job_id, document_id=document_id, status=JobStatus.PENDING)

    # Create the job
    with uow:
        uow.documents.add(document)
        uow.jobs.add(job)
        uow.commit()

    # Update the job status
    with uow:
        retrieved_job = uow.jobs.get(job_id)
        assert retrieved_job is not None
        retrieved_job.mark_as_processing()
        uow.commit()

    # Verify the update was persisted
    with uow:
        updated_job = uow.jobs.get(job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.started_at is not None


def test_uow_context_manager_properly_closes_session(uow: SqlAlchemyUnitOfWork):
    """Test that the context manager properly closes the session"""
    document_id = generate_id()
    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(document)
        uow.commit()
        # Session should be created here
        assert hasattr(uow, "session")

    # After exiting context, we should be able to use uow again
    # This tests that the session was properly closed
    with uow:
        retrieved = uow.documents.get(document_id)
        assert retrieved is not None


def test_explicit_rollback_discards_changes(uow: SqlAlchemyUnitOfWork):
    """Test that calling rollback() explicitly discards changes"""
    document_id = generate_id()
    document = Document(
        id=document_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    with uow:
        uow.documents.add(document)
        # Explicitly rollback instead of commit
        uow.rollback()

    # Verify the document was not persisted
    with uow:
        retrieved = uow.documents.get(document_id)
        assert retrieved is None
