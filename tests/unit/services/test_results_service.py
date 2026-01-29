import io
from pathlib import Path

import pytest

from core.domain import enums, model, structs
from core.service_layer.services import results
from core.service_layer.uow import AbstractUnitOfWork
from tests.fakes.repositories import (
    FakeDocumentRepository,
    FakeOcrJobRepository,
    FakeOcrResultRepository,
    FakeOutboxRepository,
)
from tests.fakes.storages import FakeFileStorage


@pytest.fixture
def uow():
    fake_docs = FakeDocumentRepository()
    fake_jobs = FakeOcrJobRepository()
    fake_results = FakeOcrResultRepository()

    class FakeUoW(AbstractUnitOfWork):
        documents = fake_docs
        jobs = fake_jobs
        results = fake_results
        outbox = FakeOutboxRepository()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.rollback()
            return None

        def commit(self):
            return None

        def rollback(self) -> None:
            return None

    return FakeUoW()


def test_get_latest_result_for_document_returns_none_when_no_completed_jobs(uow):
    doc = model.Document(
        id="doc-1", file_type=enums.FileType.PDF, file_path="/tmp/doc.pdf"
    )
    uow.documents.add(doc)

    assert results.get_latest_result_for_document(doc.id, uow) is None


def test_get_latest_result_for_document_returns_none_when_job_has_no_result(uow):
    doc = model.Document(
        id="doc-2", file_type=enums.FileType.PDF, file_path="/tmp/doc.pdf"
    )
    job = model.Job(id="job-2", document_id=doc.id, status=enums.JobStatus.COMPLETED)
    uow.documents.add(doc)
    uow.jobs.add(job)

    assert results.get_latest_result_for_document(doc.id, uow) is None


def test_get_latest_result_for_document_returns_result(uow):
    doc = model.Document(
        id="doc-3", file_type=enums.FileType.PDF, file_path="/tmp/doc.pdf"
    )
    job = model.Job(id="job-3", document_id=doc.id, status=enums.JobStatus.COMPLETED)

    processed_page = model.ProcessedPage(
        ref=model.PageRef(document_id=doc.id, index=0),
        result=model.PagePart(
            parts=[
                model.TextPart(
                    text="hello",
                    bbox=model.BoundingBox(0.0, 0.0, 1.0, 1.0),
                    confidence=1.0,
                    level="block",
                )
            ],
            metadata=model.PageMetadata(page_number=1, width=10, height=10),
        ),
    )
    result = model.Result(id="result-1", job_id=job.id, content=[processed_page])

    uow.documents.add(doc)
    uow.jobs.add(job)
    uow.results.add(result)

    dto = results.get_latest_result_for_document(doc.id, uow)

    assert dto is not None
    assert isinstance(dto, structs.ResultDTO)
    assert dto.job_id == job.id


def test_download_document_streams_file_chunks(tmp_path: Path):
    file_path = tmp_path / "file.pdf"
    file_path.write_bytes(b"chunk1chunk2")

    doc = model.Document(
        id="doc-4",
        file_type=enums.FileType.PDF,
        file_path=str(file_path),
        original_filename="file.pdf",
        file_size_bytes=len(b"chunk1chunk2"),
    )

    storage = FakeFileStorage()
    storage.files[str(file_path)] = file_path.read_bytes()

    doc_repo = FakeDocumentRepository()
    doc_repo.add(doc)
    dummy_jobs = FakeOcrJobRepository()
    dummy_results = FakeOcrResultRepository()
    dummy_outbox = FakeOutboxRepository()

    class FakeUoW(AbstractUnitOfWork):
        documents = doc_repo
        jobs = dummy_jobs
        results = dummy_results
        outbox = dummy_outbox

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.rollback()
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

    fake_uow = FakeUoW()

    stream, content_type, filename = results.download_document(
        doc.id, storage, fake_uow
    )

    chunks = b"".join(list(stream))
    assert chunks == b"chunk1chunk2"
    assert content_type == enums.FileType.PDF.value
    assert filename == "file.pdf"
