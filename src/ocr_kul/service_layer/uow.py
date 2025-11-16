import abc
from types import TracebackType
from typing import final, override, Self

from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm.session import sessionmaker, Session

from ocr_kul.adapters import repository
from ocr_kul.adapters.repository import (
    AbstractDocumentRepository,
    AbstractOCRJobRepository,
    AbstractOCRResultRepository,
)
from ocr_kul.service_layer.config import get_sqlite3_uri


class AbstractUnitOfWork(abc.ABC):
    jobs: AbstractOCRJobRepository
    documents: AbstractDocumentRepository
    results: AbstractOCRResultRepository

    @abc.abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.rollback()

    @abc.abstractmethod
    def commit(self) -> None:
        raise NotImplementedError


@final
class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.jobs = repository.FakeOcrJobRepository()
        self.documents = repository.FakeDocumentRepository()
        self.results = repository.FakeOcrResultRepository()
        self.commited: bool = False

    @override
    def rollback(self):
        pass

    @override
    def __enter__(self) -> Self:
        return self

    @override
    def commit(self) -> None:
        self.commited = True


DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(
        get_sqlite3_uri(),
        isolation_level="SERIALIZABLE",
    )
)


@final
class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self, session_factory: sessionmaker[Session] = DEFAULT_SESSION_FACTORY
    ):
        self.session_factory = session_factory
        self.session: Session

    @override
    def __enter__(self) -> Self:
        self.session = self.session_factory()
        self.jobs = repository.SQLAlchemyOcrJobRepository(self.session)
        self.documents = repository.SQLAlchemyDocumentRepository(self.session)
        self.results = repository.SQLAlchemyOcrResultRepository(self.session)
        return self

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        super().__exit__(exc_type, exc_val, exc_tb)
        self.session.close()

    @override
    def commit(self) -> None:
        self.session.commit()

    @override
    def rollback(self) -> None:
        self.session.rollback()
