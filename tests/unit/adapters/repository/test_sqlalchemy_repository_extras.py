from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.adapters.database import orm
from core.adapters.database.repository import (
    DocumentNotFoundError,
    OCRJobNotFoundError,
)
from core.domain import enums, model
from core.service_layer.uow import SqlAlchemyUnitOfWork


@pytest.fixture()
def sa_uow(tmp_path: Path) -> SqlAlchemyUnitOfWork:
    db_uri = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(db_uri, isolation_level="SERIALIZABLE")
    orm.start_mappers()
    orm.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return SqlAlchemyUnitOfWork(session_factory=session_factory)


def test_get_or_raise_document_not_found_raises(sa_uow: SqlAlchemyUnitOfWork):
    with sa_uow:
        with pytest.raises(DocumentNotFoundError):
            sa_uow.documents.get_or_raise("missing-doc")


def test_get_or_raise_job_not_found_raises(sa_uow: SqlAlchemyUnitOfWork):
    with sa_uow:
        with pytest.raises(OCRJobNotFoundError):
            sa_uow.jobs.get_or_raise("missing-job")


def test_get_latest_completed_for_document_returns_newest(sa_uow: SqlAlchemyUnitOfWork):
    doc = model.Document(
        id="doc-a", file_type=enums.FileType.PDF, file_path="/tmp/doc.pdf"
    )
    older_job = model.Job(
        id="job-old", document_id=doc.id, status=enums.JobStatus.COMPLETED
    )
    older_job.completed_at = datetime.now() - timedelta(days=1)
    newer_job = model.Job(
        id="job-new", document_id=doc.id, status=enums.JobStatus.COMPLETED
    )
    newer_job.completed_at = datetime.now()

    doc_id = doc.id

    with sa_uow:
        sa_uow.documents.add(doc)
        sa_uow.jobs.add(older_job)
        sa_uow.jobs.add(newer_job)
        sa_uow.commit()

    with sa_uow:
        latest = sa_uow.jobs.get_latest_completed_for_document(doc_id)
        assert latest is not None
        assert latest.id == newer_job.id


def test_delete_with_cascade_removes_results(sa_uow: SqlAlchemyUnitOfWork):
    doc = model.Document(
        id="doc-b", file_type=enums.FileType.PDF, file_path="/tmp/doc.pdf"
    )
    job = model.Job(id="job-del", document_id=doc.id, status=enums.JobStatus.COMPLETED)
    processed_page = model.ProcessedPage(
        ref=model.PageRef(document_id=doc.id, index=0),
        result=model.PagePart(
            parts=[], metadata=model.PageMetadata(page_number=1, width=1, height=1)
        ),
    )
    result = model.Result(id="res-del", job_id=job.id, content=[processed_page])

    job_id = job.id

    with sa_uow:
        sa_uow.documents.add(doc)
        sa_uow.jobs.add(job)
        sa_uow.results.add(result)
        sa_uow.commit()

    with sa_uow:
        fetched_job = sa_uow.jobs.get(job_id)
        assert fetched_job is not None
        sa_uow.jobs.delete_with_cascade(fetched_job)
        sa_uow.commit()

    with sa_uow:
        assert sa_uow.jobs.get(job_id) is None
        assert sa_uow.results.get_by_job_id(job_id) is None


def test_list_by_filters_orders_by_created_at_desc(sa_uow: SqlAlchemyUnitOfWork):
    doc = model.Document(
        id="doc-c", file_type=enums.FileType.PDF, file_path="/tmp/doc.pdf"
    )
    jobs = [
        model.Job(id=f"job-{idx}", document_id=doc.id, status=enums.JobStatus.PENDING)
        for idx in range(3)
    ]
    for idx, job in enumerate(jobs):
        job.created_at = datetime.now() - timedelta(minutes=idx)

    with sa_uow:
        sa_uow.documents.add(doc)
        for job in jobs:
            sa_uow.jobs.add(job)
        sa_uow.commit()

    with sa_uow:
        listed = sa_uow.jobs.list_by_filters(
            status=enums.JobStatus.PENDING, skip=0, limit=2
        )
        assert len(listed) == 2
        # Should be ordered by created_at desc so first element has smallest idx
        assert listed[0].created_at >= listed[1].created_at
