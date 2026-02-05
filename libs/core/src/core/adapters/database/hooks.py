"""SQLAlchemy session hooks to collect and relay outbox tasks after commit."""

from collections.abc import Iterable
from typing import TypedDict

from sqlalchemy import event, orm

from core.adapters.queue.runner import CeleryTaskRunner
from core.domain import dto, model
from core.utils.logger import get_logger

logger = get_logger(__name__)


class SessionInfo(TypedDict):
    tasks: list[dto.OutboxEntryDTO]


def _new_outbox_entries(session: orm.Session) -> Iterable[model.OutboxEntry]:
    return (obj for obj in session.new if isinstance(obj, model.OutboxEntry))


@event.listens_for(orm.Session, "before_commit")
def collect_outbox_tasks(session: orm.Session) -> None:
    tasks = [
        dto.OutboxEntryDTO.from_domain(entry) for entry in _new_outbox_entries(session)
    ]
    session.info["tasks"] = tasks
    logger.info("Collected outbox tasks before commit", tasks_num=len(tasks))


@event.listens_for(orm.Session, "after_commit")
def schedule_outbox_tasks(session: orm.Session) -> None:
    tasks: list[dto.OutboxEntryDTO] = session.info.pop("tasks", [])
    if not tasks:
        return

    runner = CeleryTaskRunner()
    for task in tasks:
        logger.info(
            "Scheduling task after commit",
            task_id=task.id,
            event_type=task.event_type.value,
        )
        runner.schedule_task(task)
