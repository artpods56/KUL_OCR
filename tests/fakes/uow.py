from typing import final, override, Self

from kul_ocr.service_layer.uow import AbstractUnitOfWork
from tests.fakes import repositories


@final
class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.documents = repositories.FakeDocumentRepository()
        self.results = repositories.FakeOcrResultRepository()
        self.jobs = repositories.FakeOcrJobRepository(results_repo=self.results)
        self.committed: bool = False

    @override
    def rollback(self):
        pass

    @override
    def __enter__(self) -> Self:
        return self

    @override
    def commit(self) -> None:
        self.committed = True
