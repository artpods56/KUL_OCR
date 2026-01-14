import abc
from collections.abc import Sequence
from typing import final, override

from sqlalchemy import select
from sqlalchemy.orm.session import Session

from kul_ocr.adapters.database import orm
from kul_ocr.domain import model
from kul_ocr.domain.model import JobStatus

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
    def list_all(self) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_document_id(self, document_id: str) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_terminal_jobs(self) -> Sequence[model.Job]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_latest_completed_for_document(self, document_id: str) -> model.Job | None:
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
    def list_all(self) -> Sequence[model.Job]:
        statement = select(model.Job)
        return self._session.scalars(statement).all()

    @override
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.Job]:
        statement = select(model.Job).where(orm.ocr_jobs.c.status == job_status)
        return self._session.scalars(statement).all()

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.Job]:
        statement = select(model.Job).where(orm.ocr_jobs.c.document_id == document_id)
        return self._session.scalars(statement).all()

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
