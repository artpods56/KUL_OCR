from typing import Protocol, runtime_checkable

from kul_ocr.domain import model


@runtime_checkable
class TaskRunner(Protocol):
    def schedule_task(self, entry: model.OutboxEntry) -> None: ...

    def revoke_task(self, task_id: str) -> None: ...
