import abc
from collections.abc import Sequence
from datetime import datetime
from typing import final, override

from sqlalchemy import select
from sqlalchemy.orm.session import Session

from core.adapters.database import orm
from core.domain import enums, model
from core.domain.enums import JobStatus
from core.domain.exceptions import DomainException


# --- Abstract Repositories ---


class AbstractDocumentRepository(abc.ABC):
    """Abstract base class defining the interface for Document repositories."""

    @abc.abstractmethod
    def add(self, document: model.Document) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, document_id: str) -> model.Document | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_raise(self, document_id: str) -> model.Document:
        """Get document by ID or raise DocumentNotFoundError."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[model.Document]:
        raise NotImplementedError


class AbstractOCRJobRepository(abc.ABC):
    """Abstract base class defining the interface for OCR job repositories."""

    @abc.abstractmethod
    def add(self, ocr_job: model.Job) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ocr_job_id: str) -> model.Job | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_raise(self, job_id: str) -> model.Job:
        """Get job by ID or raise OCRJobNotFoundError."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_status(self, job_status: enums.JobStatus) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_document_id(self, document_id: str) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_filters(
        self,
        status: enums.JobStatus | None = None,
        document_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[model.Job]:
        """List jobs filtered by optional status and/or document_id with pagination."""
        raise NotImplementedError

    @abc.abstractmethod
    def count_by_filters(
        self,
        status: enums.JobStatus | None = None,
        document_id: str | None = None,
    ) -> int:
        """Count total jobs matching the filters."""
        raise NotImplementedError

    @abc.abstractmethod
    def has_active_job_for_document(self, document_id: str) -> bool:
        """Check if document has any active (pending/processing) jobs."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_terminal_jobs(self) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_latest_completed_for_document(self, document_id: str) -> model.Job | None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, ocr_job: model.Job) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete_with_cascade(self, job: model.Job) -> None:
        """Delete job and associated results in single atomic operation."""
        raise NotImplementedError


class AbstractOCRResultRepository(abc.ABC):
    """Abstract base class defining the interface for OCR result repositories."""

    @abc.abstractmethod
    def add(self, ocr_result: model.Result) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ocr_result_id: str) -> model.Result | None:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[model.Result]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_job_id(self, job_id: str) -> model.Result | None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, ocr_result: model.Result) -> None:
        raise NotImplementedError


# --- SQL Alchemy Repositories ---


@final
class SQLAlchemyDocumentRepository(AbstractDocumentRepository):
    """Repository for managing Document entities using SQLAlchemy."""

    def __init__(self, session: Session):
        self._session = session

    @override
    def add(self, document: model.Document) -> None:
        self._session.add(document)

    @override
    def get(self, document_id: str) -> model.Document | None:
        statement = select(model.Document).where(orm.documents.c.id == document_id)
        return self._session.scalars(statement).first()

    @override
    def get_or_raise(self, document_id: str) -> model.Document:
        document = self.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)
        return document

    @override
    def list_all(self) -> Sequence[model.Document]:
        statement = select(model.Document)
        return self._session.scalars(statement).all()


@final
class SQLAlchemyOcrJobRepository(AbstractOCRJobRepository):
    """Repository for managing Job entities using SQLAlchemy."""

    def __init__(self, session: Session):
        self._session = session

    @override
    def add(self, ocr_job: model.Job):
        self._session.add(ocr_job)

    @override
    def get(self, ocr_job_id: str) -> model.Job | None:
        statement = select(model.Job).where(orm.ocr_jobs.c.id == ocr_job_id)
        return self._session.scalar(statement)

    @override
    def get_or_raise(self, job_id: str) -> model.Job:
        job = self.get(job_id)
        if job is None:
            raise OCRJobNotFoundError(job_id=job_id)
        return job

    @override
    def list_all(self) -> Sequence[model.Job]:
        statement = select(model.Job)
        return self._session.scalars(statement).all()

    @override
    def list_by_status(self, job_status: enums.JobStatus) -> Sequence[model.Job]:
        statement = select(model.Job).where(orm.ocr_jobs.c.status == job_status)
        return self._session.scalars(statement).all()

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.Job]:
        statement = select(model.Job).where(orm.ocr_jobs.c.document_id == document_id)
        return self._session.scalars(statement).all()

    @override
    def list_by_filters(
        self,
        status: enums.JobStatus | None = None,
        document_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[model.Job]:
        statement = select(model.Job)
        if status is not None:
            statement = statement.where(orm.ocr_jobs.c.status == status)
        if document_id is not None:
            statement = statement.where(orm.ocr_jobs.c.document_id == document_id)

        # Add ordering for consistent pagination
        statement = statement.order_by(orm.ocr_jobs.c.created_at.desc())

        # Add pagination
        statement = statement.offset(skip).limit(limit)

        return self._session.scalars(statement).all()

    @override
    def count_by_filters(
        self,
        status: enums.JobStatus | None = None,
        document_id: str | None = None,
    ) -> int:
        from sqlalchemy import func

        statement = select(func.count()).select_from(orm.ocr_jobs)
        if status is not None:
            statement = statement.where(orm.ocr_jobs.c.status == status)
        if document_id is not None:
            statement = statement.where(orm.ocr_jobs.c.document_id == document_id)

        result = self._session.execute(statement).scalar()
        return result if result is not None else 0

    @override
    def has_active_job_for_document(self, document_id: str) -> bool:
        statement = select(model.Job).where(
            orm.ocr_jobs.c.document_id == document_id,
            orm.ocr_jobs.c.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
        )
        return self._session.scalar(select(statement.exists())) or False

    @override
    def list_terminal_jobs(self) -> Sequence[model.Job]:
        statement = select(model.Job).where(
            orm.ocr_jobs.c.status.in_([JobStatus.FAILED, JobStatus.COMPLETED])
        )
        return self._session.scalars(statement).all()

    @override
    def get_latest_completed_for_document(self, document_id: str) -> model.Job | None:
        statement = (
            select(model.Job)
            .where(
                orm.ocr_jobs.c.document_id == document_id,
                orm.ocr_jobs.c.status == JobStatus.COMPLETED,
            )
            .order_by(orm.ocr_jobs.c.completed_at.desc())
            .limit(1)
        )
        return self._session.scalar(statement)

    @override
    def delete(self, ocr_job: model.Job) -> None:
        self._session.delete(ocr_job)

    @override
    def delete_with_cascade(self, job: model.Job) -> None:
        """Delete job and associated results explicitly."""
        # Delete results first (FK constraint)
        result_statement = select(model.Result).where(
            orm.ocr_results.c.job_id == job.id
        )
        results = self._session.scalars(result_statement).all()
        for result in results:
            self._session.delete(result)
        # Then delete job
        self._session.delete(job)


@final
class SQLAlchemyOcrResultRepository(AbstractOCRResultRepository):
    """Repository for managing Result entities using SQLAlchemy."""

    def __init__(self, session: Session):
        self._session = session

    @override
    def add(self, ocr_result: model.Result) -> None:
        self._session.add(ocr_result)

    @override
    def get(self, ocr_result_id: str) -> model.Result | None:
        statement = select(model.Result).where(orm.ocr_results.c.id == ocr_result_id)
        return self._session.scalar(statement)

    @override
    def list_all(self) -> Sequence[model.Result]:
        statement = select(model.Result)
        return self._session.scalars(statement).all()

    @override
    def get_by_job_id(self, job_id: str) -> model.Result | None:
        statement = select(model.Result).where(orm.ocr_results.c.job_id == job_id)
        return self._session.scalar(statement)

    @override
    def delete(self, ocr_result: model.Result) -> None:
        self._session.delete(ocr_result)


class AbstractOutboxRepository(abc.ABC):
    """Abstract base class defining the interface for Outbox repositories."""

    @abc.abstractmethod
    def add(self, entry: model.OutboxEntry) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, entry_id: str) -> model.OutboxEntry | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_raise(self, entry_id: str) -> model.OutboxEntry:
        """Get outbox entry by ID or raise OutboxEntryNotFoundError."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_pending(self, limit: int = 100) -> Sequence[model.OutboxEntry]:
        """List pending (not yet relayed) outbox entries."""
        raise NotImplementedError

    @abc.abstractmethod
    def mark_as_relayed(self, entry_id: str) -> None:
        """Mark an outbox entry as relayed."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_relayed_older_than(self, cutoff: datetime) -> int:
        """Delete relayed entries older than the cutoff time. Returns count deleted."""
        raise NotImplementedError


@final
class SQLAlchemyOutboxRepository(AbstractOutboxRepository):
    """Repository for managing OutboxEntry entities using SQLAlchemy."""

    def __init__(self, session: Session):
        self._session = session

    @override
    def add(self, entry: model.OutboxEntry) -> None:
        self._session.add(entry)

    @override
    def get(self, entry_id: str) -> model.OutboxEntry | None:
        statement = select(model.OutboxEntry).where(orm.outbox_entries.c.id == entry_id)
        return self._session.scalar(statement)

    @override
    def get_or_raise(self, entry_id: str) -> model.OutboxEntry:
        entry = self.get(entry_id)
        if entry is None:
            raise OutboxEntryNotFoundError(entry_id=entry_id)
        return entry

    @override
    def list_pending(self, limit: int = 100) -> Sequence[model.OutboxEntry]:
        statement = (
            select(model.OutboxEntry)
            .where(orm.outbox_entries.c.relayed_at.is_(None))
            .order_by(orm.outbox_entries.c.created_at.asc())
            .limit(limit)
        )
        return self._session.scalars(statement).all()

    @override
    def mark_as_relayed(self, entry_id: str) -> None:
        entry = self.get_or_raise(entry_id)
        entry.mark_as_relayed()

    @override
    def delete_relayed_older_than(self, cutoff: datetime) -> int:
        statement = select(model.OutboxEntry).where(
            orm.outbox_entries.c.relayed_at.isnot(None),
            orm.outbox_entries.c.relayed_at < cutoff,
        )
        entries = self._session.scalars(statement).all()
        count = len(entries)
        for entry in entries:
            self._session.delete(entry)
        return count


class DocumentNotFoundError(DomainException):
    code: str = "DOCUMENT_NOT_FOUND"

    def __init__(self, document_id: str, message: str | None = None):
        msg = message or f"Document not found: {document_id}"
        super().__init__(message=msg, document_id=document_id)


class OCRJobNotFoundError(DomainException):
    code: str = "OCR_JOB_NOT_FOUND"

    def __init__(self, job_id: str, message: str | None = None):
        msg = message or f"OCR job not found: {job_id}"
        super().__init__(message=msg, job_id=job_id)


class OutboxEntryNotFoundError(DomainException):
    code: str = "OUTBOX_ENTRY_NOT_FOUND"

    def __init__(self, entry_id: str, message: str | None = None):
        msg = message or f"Outbox entry not found: {entry_id}"
        super().__init__(message=msg, entry_id=entry_id)
