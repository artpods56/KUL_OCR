from typing import final
from core.domain import protocols
from core.adapters.database import hooks
from core.adapters.queue import runner

from sqlalchemy import orm


@final
class AppSession(orm.Session): ...


HOOKS: list[protocols.SessionHook] = [
    hooks.CollectAndScheduleTasksHook(runner.CeleryTaskRunner()),
]


def register_hooks(session_class: type[orm.Session]):
    for hook in HOOKS:
        hook(session_class)


register_hooks(AppSession)

SessionLocal = orm.sessionmaker(class_=AppSession)


def get_session() -> AppSession:
    session = SessionLocal()
    return session
