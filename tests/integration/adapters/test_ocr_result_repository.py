import pytest

from kul_ocr.domain.model import (
    BoundingBox,
    Document,
    FileType,
    Job,
    JobStatus,
    PageMetadata,
    PagePart,
    PageRef,
    ProcessedPage,
    Result,
    TextPart,
)
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def job_id(uow: SqlAlchemyUnitOfWork):
    """Create and persist a test document and OCR job, return job ID"""
    doc_id = generate_id()
    j_id = generate_id()

    doc = Document(
        id=doc_id,
        file_path="/path/to/test.pdf",
        file_type=FileType.PDF,
        file_size_bytes=1024,
    )

    job = Job(id=j_id, document_id=doc_id, status=JobStatus.PENDING)

    with uow:
        uow.documents.add(doc)
        uow.jobs.add(job)
        uow.commit()

    return j_id


def test_can_add_and_retrieve_simple_ocr_result(uow: SqlAlchemyUnitOfWork, job_id: str):
    """Test adding a simple OCR result to the database and retrieving it"""
    result_id = generate_id()

    processed_page = ProcessedPage(
        ref=PageRef(document_id="doc-1", index=0),
        result=PagePart(
            parts=[
                TextPart(
                    text="This is the OCR text content",
                    bbox=BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0),
                    confidence=0.95,
                    level="block",
                )
            ],
            metadata=PageMetadata(page_number=1, width=100, height=50),
        ),
    )

    result = Result(id=result_id, job_id=job_id, content=[processed_page])

    with uow:
        uow.results.add(result)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        retrieved = uow.results.get(result_id)
        assert retrieved is not None
        assert retrieved.id == result_id
        assert retrieved.job_id == job_id
        assert len(retrieved.content) == 1
        assert retrieved.content[0].result.full_text == "This is the OCR text content"


def test_can_list_all_results(uow: SqlAlchemyUnitOfWork, job_id: str):
    """Test listing all OCR results from the database"""
    result_ids = [generate_id() for _ in range(3)]
    results = [
        Result(
            id=result_ids[i],
            job_id=job_id,
            content=[
                ProcessedPage(
                    ref=PageRef(document_id="doc-1", index=0),
                    result=PagePart(
                        parts=[
                            TextPart(
                                text=f"OCR content {i}",
                                bbox=BoundingBox(
                                    x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0
                                ),
                                confidence=0.95,
                                level="block",
                            )
                        ],
                        metadata=PageMetadata(page_number=1, width=100, height=50),
                    ),
                )
            ],
        )
        for i in range(3)
    ]

    with uow:
        for result in results:
            uow.results.add(result)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        all_results = uow.results.list_all()
        assert len(all_results) == 3
        assert {r.id for r in all_results} == set(result_ids)


def test_get_returns_none_for_nonexistent_result(uow: SqlAlchemyUnitOfWork):
    """Test that get returns None for a result that doesn't exist"""
    with uow:
        result = uow.results.get("nonexistent-id")
        assert result is None


def test_can_store_and_retrieve_multipage_ocr_result(
    uow: SqlAlchemyUnitOfWork, job_id: str
):
    """Test storing and retrieving multipage OCR results"""
    result_id = generate_id()

    pages = [
        ProcessedPage(
            ref=PageRef(document_id="doc-1", index=0),
            result=PagePart(
                parts=[
                    TextPart(
                        text="Content of page 1",
                        bbox=BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0),
                        confidence=0.95,
                        level="block",
                    )
                ],
                metadata=PageMetadata(page_number=1, width=100, height=50),
            ),
        ),
        ProcessedPage(
            ref=PageRef(document_id="doc-1", index=1),
            result=PagePart(
                parts=[
                    TextPart(
                        text="Content of page 2",
                        bbox=BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0),
                        confidence=0.95,
                        level="block",
                    )
                ],
                metadata=PageMetadata(page_number=2, width=100, height=50),
            ),
        ),
        ProcessedPage(
            ref=PageRef(document_id="doc-1", index=2),
            result=PagePart(
                parts=[
                    TextPart(
                        text="Content of page 3",
                        bbox=BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0),
                        confidence=0.95,
                        level="block",
                    )
                ],
                metadata=PageMetadata(page_number=3, width=100, height=50),
            ),
        ),
    ]

    result = Result(id=result_id, job_id=job_id, content=pages)

    with uow:
        uow.results.add(result)
        uow.commit()

    # Retrieve in a new transaction
    with uow:
        retrieved = uow.results.get(result_id)
        assert retrieved is not None
        assert retrieved.id == result_id
        assert len(retrieved.content) == 3
        assert retrieved.content[0].ref.index == 0
        assert retrieved.content[0].result.full_text == "Content of page 1"


def test_multiple_results_for_different_jobs(uow: SqlAlchemyUnitOfWork):
    """Test storing results for multiple different jobs"""
    # Create two documents and jobs
    doc1_id = generate_id()
    doc2_id = generate_id()
    job1_id = generate_id()
    job2_id = generate_id()
    result1_id = generate_id()
    result2_id = generate_id()

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

    job1 = Job(id=job1_id, document_id=doc1_id, status=JobStatus.COMPLETED)
    job2 = Job(id=job2_id, document_id=doc2_id, status=JobStatus.COMPLETED)

    result1 = Result(
        id=result1_id,
        job_id=job1_id,
        content=[
            ProcessedPage(
                ref=PageRef(document_id=doc1_id, index=0),
                result=PagePart(
                    parts=[
                        TextPart(
                            text="Result for job 1",
                            bbox=BoundingBox(
                                x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0
                            ),
                            confidence=0.95,
                            level="block",
                        )
                    ],
                    metadata=PageMetadata(page_number=1, width=100, height=50),
                ),
            )
        ],
    )
    result2 = Result(
        id=result2_id,
        job_id=job2_id,
        content=[
            ProcessedPage(
                ref=PageRef(document_id=doc2_id, index=0),
                result=PagePart(
                    parts=[
                        TextPart(
                            text="Result for job 2",
                            bbox=BoundingBox(
                                x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0
                            ),
                            confidence=0.95,
                            level="block",
                        )
                    ],
                    metadata=PageMetadata(page_number=1, width=100, height=50),
                ),
            )
        ],
    )

    with uow:
        uow.documents.add(doc1)
        uow.documents.add(doc2)
        uow.jobs.add(job1)
        uow.jobs.add(job2)
        uow.results.add(result1)
        uow.results.add(result2)
        uow.commit()

    # Verify both results are stored correctly
    with uow:
        retrieved1 = uow.results.get(result1_id)
        retrieved2 = uow.results.get(result2_id)

        assert retrieved1 is not None
        assert retrieved1.job_id == job1_id
        assert retrieved1.content[0].result.full_text == "Result for job 1"

        assert retrieved2 is not None
        assert retrieved2.job_id == job2_id
        assert retrieved2.content[0].result.full_text == "Result for job 2"
