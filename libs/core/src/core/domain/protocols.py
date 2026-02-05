from typing import Protocol, runtime_checkable

from sqlalchemy import orm

from core.domain import dto


@runtime_checkable
class TaskRunner(Protocol):
    def schedule_task(self, entry: dto.OutboxEntryDTO) -> None: ...

    def revoke_task(self, task_id: str) -> None: ...


class SessionHook(Protocol):
    def __call__(self, session_class: type[orm.Session]) -> None: ...

    @staticmethod
    def pre_commit(new_session: orm.Session) -> None: ...

    def post_commit(self, new_session: orm.Session) -> None: ...
