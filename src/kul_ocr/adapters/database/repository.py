import abc
from collections.abc import Sequence
from typing import Any, final, override

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
    """Abstract base class defining the interface for OCR result repositories."""
    @abc.abstractmethod
    def add(self, ocr_result: model.OCRResult[Any]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, ocr_result_id: str) -> model.OCRResult[Any] | None:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[model.OCRResult[Any]]:
        raise NotImplementedError


# --- SQL Alchemy Repositories ---


@final
class SQLAlchemyDocumentRepository(AbstractDocumentRepository):
    """Repository for managing Document entities using SQLAlchemy."""
    def __init__(self, session: Session):
        """Initialize the repository with a SQLAlchemy session.
        
        Args:
            session:SQLAlchemy session object used for database operations.
        """
        self._session = session

    @override
    def add(self, document: model.Document) -> None:
        """Add a new Document to the database session
        
        The document is persisted to the database when the session is committed.
        
        Args:
            document: Document instance to add.
        
        Returns: 
            None
        """
        self._session.add(document)

    @override
    def get(self, document_id: str) -> model.Document | None:
        """Retrieves a Document by its unique ID.
        
        Queries the database for a Document matching given ID
        
        Args:
            document_id: Unique identifier of the document to find.
        
        Returns: 
            The Document instance if found, else None
        """
        statement = select(model.Document).where(orm.documents.c.id == document_id)
        return self._session.scalars(statement).first()

    @override
    def list_all(self) -> Sequence[model.Document]:
        """Retrieves all Document entities from the database.
        
        Returns: 
            A sequence of all Document instances.
        """
        statement = select(model.Document)
        return self._session.scalars(statement).all()


@final
class SQLAlchemyOcrJobRepository(AbstractOCRJobRepository):
    """Repository for managing OCRJob entities using SQLAlchemy."""
    def __init__(self, session: Session):
        """Initialize the repository with a SQLAlchemy session.
        
        Args:
            session:SQLAlchemy session object used for database operations.
        """
        self._session = session

    @override
    def add(self, ocr_job: model.OCRJob):
        """Add a new OCRJob to the database session
        
        Args:
            ocr_job: OCRJob instance to add.
        
        Returns: 
            None
        """
        self._session.add(ocr_job)

    @override
    def get(self, ocr_job_id: str) -> model.OCRJob | None:
        """Retrieves a OCRJob by its unique ID.
        
        Args:
            ocr_job_id: Unique identifier of the OCRJob to find.
        
        Returns: 
            The OCRJob instance if found, else None
        """
        statement = select(model.OCRJob).where(orm.ocr_jobs.c.id == ocr_job_id)
        return self._session.scalar(statement)

    @override
    def list_all(self) -> Sequence[model.OCRJob]:
        """Retrieves all OCRJob entities from the database.
        
        Returns: 
            A sequence of all OCRJob instances.
        """
        statement = select(model.OCRJob)
        return self._session.scalars(statement).all()

    @override
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.OCRJob]:
        """Retrieves all OCRJob entities with a specific status.
        
        Args:
            job_status: The status to filter OCRJobs by.
        
        Returns: 
            A sequence of all OCRJob instances.
        """
        statement = select(model.OCRJob).where(orm.ocr_jobs.c.status == job_status)
        return self._session.scalars(statement).all()

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.OCRJob]:
        """Retrieves all OCRJobs ffor a specific decument.
        
        Args:
            document_id: Unique identifier of the accosiated document.
        
        Returns: 
            A sequence of OCRJob instances linked to the document.
        """
        statement = select(model.OCRJob).where(
            orm.ocr_jobs.c.document_id == document_id
        )
        return self._session.scalars(statement).all()

    @override
    def list_terminal_jobs(self) -> Sequence[model.OCRJob]:
        """Retrieves all OCRJobs that are ia a terminal state.
        
        Returns: 
            A sequence of OCRJob instances ia a terminal state.
        """
        select_statement = select(model.OCRJob).where(
            orm.ocr_jobs.c.status.in_([JobStatus.FAILED, JobStatus.COMPLETED])
        )
        return self._session.scalars(select_statement).all()


@final
class SQLAlchemyOcrResultRepository(AbstractOCRResultRepository):
    """Repository for managing OCRResult entities using SQLAlchemy."""
    def __init__(self, session: Session):
        """Initialize the repository with a SQLAlchemy session.
        
        Args:
            session:SQLAlchemy session object used for database operations.
        """
        self._session = session

    @override
    def add(self, ocr_result: model.OCRResult[Any]) -> None:
        """Add a new OCRResult to the database session
        
        Args:
            ocr_result: OCRResult instance to add.
        
        Returns: 
            None
        """
        self._session.add(ocr_result)

    @override
    def get(self, ocr_result_id: str) -> model.OCRResult[Any] | None:
        """Retrieves a OCRResult by its unique ID.
        
        Args:
            ocr_result_id: Unique identifier of the OCRResult to find.
        
        Returns: 
            The OCRResult instance if found, else None
        """
        statement = select(model.OCRResult).where(orm.ocr_results.c.id == ocr_result_id)
        return self._session.scalar(statement)

    @override
    def list_all(self) -> Sequence[model.OCRResult[Any]]:
        """Retrieves all OCRResult entities from the database.
        
        Returns: 
            A sequence of all OCRResult instances.
        """
        statement = select(model.OCRResult)
        return self._session.scalars(statement).all()
