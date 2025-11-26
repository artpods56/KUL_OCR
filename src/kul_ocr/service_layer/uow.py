import abc
from types import TracebackType
from typing import Self, final, override

from sqlalchemy.orm.session import Session, sessionmaker

from kul_ocr.adapters.database import repository


class AbstractUnitOfWork(abc.ABC):
    jobs: repository.AbstractOCRJobRepository
    documents: repository.AbstractDocumentRepository
    results: repository.AbstractOCRResultRepository

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
class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]):
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
