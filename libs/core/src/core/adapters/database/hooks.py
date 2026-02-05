from core.domain import model, dto, protocols
from sqlalchemy import orm


class CollectAndScheduleTasksHook:
    def __init__(self, task_runner: protocols.TaskRunner) -> None:
        self._task_runner = task_runner

    def __call__(self, session_class: type[orm.Session]) -> None:
        from sqlalchemy import event

        event.listen(session_class, "before_commit", self.pre_commit)
        event.listen(session_class, "after_commit", self.post_commit)

    @staticmethod
    def pre_commit(new_session: orm.Session) -> None:
        tasks = [
            dto.OutboxEntryDTO.from_domain(obj)
            for obj in new_session.new
            if isinstance(obj, model.OutboxEntry)
        ]
        new_session.info["outbox_tasks"] = tasks

    def post_commit(self, new_session: orm.Session) -> None:
        tasks = new_session.info.pop("outbox_tasks", [])

        for task in tasks:
            self._task_runner.schedule_task(task)
