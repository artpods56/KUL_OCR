import abc
from collections.abc import Sequence
from typing import override, Any, final

from sqlalchemy import select
from sqlalchemy.orm.session import Session

from ocr_kul.adapters import orm
from ocr_kul.domain import model
from ocr_kul.domain.model import JobStatus


# --- Abstract Repositories ---


class AbstractDocumentRepository(abc.ABC):
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
    @abc.abstractmethod
    def add(self, ocr_job: model.OCRJob) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ocr_job_id: str) -> model.OCRJob | None:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[model.OCRJob]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.OCRJob]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_by_document_id(self, document_id: str) -> Sequence[model.OCRJob]:
        raise NotImplementedError

    @abc.abstractmethod
    def list_terminal_jobs(self) -> Sequence[model.OCRJob]:
        raise NotImplementedError


class AbstractOCRResultRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, ocr_result: model.OCRResult[Any]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ocr_result_id: str) -> model.OCRResult[Any] | None:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[model.OCRResult[Any]]:
        raise NotImplementedError


# --- Fake Repositories ---


class FakeDocumentRepository(AbstractDocumentRepository):
    def __init__(self):
        self._documents: dict[str, model.Document] = {}

    @override
    def add(self, document: model.Document):
        self._documents[document.id] = document

    @override
    def get(self, document_id: str):
        return self._documents.get(document_id, None)

    @override
    def list_all(self) -> Sequence[model.Document]:
        return list(self._documents.values())


class FakeOcrJobRepository(AbstractOCRJobRepository):
    def __init__(self):
        self._ocr_jobs: dict[str, model.OCRJob] = {}

    @override
    def add(self, ocr_job: model.OCRJob):
        self._ocr_jobs[ocr_job.id] = ocr_job

    @override
    def get(self, ocr_job_id: str) -> model.OCRJob | None:
        return self._ocr_jobs.get(ocr_job_id, None)

    @override
    def list_all(self) -> Sequence[model.OCRJob]:
        return list(self._ocr_jobs.values())

    @override
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.OCRJob]:
        return [job for job in self._ocr_jobs.values() if job.status == job_status]

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.OCRJob]:
        return [
            job for job in self._ocr_jobs.values() if job.document_id == document_id
        ]

    @override
    def list_terminal_jobs(self) -> Sequence[model.OCRJob]:
        return [job for job in self._ocr_jobs.values() if job.is_terminal]


class FakeOcrResultRepository(AbstractOCRResultRepository):
    def __init__(self):
        self._ocr_results: dict[str, model.OCRResult[Any]] = {}

    @override
    def add(self, ocr_result: model.OCRResult[Any]) -> None:
        self._ocr_results[ocr_result.id] = ocr_result

    @override
    def get(self, ocr_result_id: str) -> model.OCRResult[Any] | None:
        return self._ocr_results.get(ocr_result_id, None)

    @override
    def list_all(self) -> Sequence[model.OCRResult[Any]]:
        return list(self._ocr_results.values())


# --- SQL Alchemy Repositories ---


@final
class SQLAlchemyDocumentRepository(AbstractDocumentRepository):
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
    def __init__(self, session: Session):
        self._session = session

    @override
    def add(self, ocr_job: model.OCRJob):
        self._session.add(ocr_job)

    @override
    def get(self, ocr_job_id: str) -> model.OCRJob | None:
        statement = select(model.OCRJob).where(orm.ocr_jobs.c.id == ocr_job_id)
        return self._session.scalar(statement)

    @override
    def list_all(self) -> Sequence[model.OCRJob]:
        statement = select(model.OCRJob)
        return self._session.scalars(statement).all()

    @override
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.OCRJob]:
        statement = select(model.OCRJob).where(orm.ocr_jobs.c.status == job_status)
        return self._session.scalars(statement).all()

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.OCRJob]:
        statement = select(model.OCRJob).where(
            orm.ocr_jobs.c.document_id == document_id
        )
        return self._session.scalars(statement).all()

    @override
    def list_terminal_jobs(self) -> Sequence[model.OCRJob]:
        select_statement = select(model.OCRJob).where(
            orm.ocr_jobs.c.status.in_([JobStatus.FAILED, JobStatus.COMPLETED])
        )
        return self._session.scalars(select_statement).all()


@final
class SQLAlchemyOcrResultRepository(AbstractOCRResultRepository):
    def __init__(self, session: Session):
        self._session = session

    @override
    def add(self, ocr_result: model.OCRResult[Any]) -> None:
        self._session.add(ocr_result)

    @override
    def get(self, ocr_result_id: str) -> model.OCRResult[Any] | None:
        statement = select(model.OCRResult).where(orm.ocr_results.c.id == ocr_result_id)
        return self._session.scalar(statement)

    @override
    def list_all(self) -> Sequence[model.OCRResult[Any]]:
        statement = select(model.OCRResult)
        return self._session.scalars(statement).all()
