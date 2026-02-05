from typing import override

from core.domain import model, protocols, dto


class CeleryTaskRunner(protocols.TaskRunner):
    @override
    def schedule_task(self, entry: dto.OutboxEntryDTO | model.OutboxEntry) -> None:
        from worker.main import app

        entry_dto = (
            entry
            if isinstance(entry, dto.OutboxEntryDTO)
            else dto.OutboxEntryDTO.from_domain(entry)
        )

        task_name = model.TASK_NAMES.get(entry_dto.event_type)
        if task_name is None:
            raise ValueError(
                f"No task configured for event type: {entry_dto.event_type}"
            )

        _ = app.send_task(
            task_name,
            task_id=entry_dto.id,
            kwargs={**entry_dto.payload},
        )

    @override
    def revoke_task(self, task_id: str) -> None:
        from worker.main import app

        _ = app.control.revoke(task_id, terminate=True)
