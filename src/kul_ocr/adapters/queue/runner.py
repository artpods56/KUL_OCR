from typing import cast, override

from kul_ocr.domain import model, protocols, enums


class CeleryTaskRunner(protocols.TaskRunner):
    @override
    def schedule_task(self, entry: model.OutboxEntry) -> None:
        from kul_ocr.entrypoints.celery_app import app

        task_name = model.TASK_NAMES.get(entry.event_type)
        if task_name is None:
            raise ValueError(f"No task configured for event type: {entry.event_type}")

        _ = app.send_task(
            task_name,
            task_id=entry.id,
            kwargs={**entry.payload},
        )

        # match entry.event_type:
        #     case enums.OutboxEventType.JOB_SCHEDULING:
        #
        #         _ = app.send_task(
        #             task_name,
        #             task_id=entry.id,
        #             kwargs={**entry.payload},
        #         )
        #     case enums.OutboxEventType.DOCUMENT_UPLOAD:
        #
        #
        #         _ = app.send_task(
        #             task_name,
        #             task_id=entry.id,
        #             kwargs={**payload},
        #         )

    @override
    def revoke_task(self, task_id: str) -> None:
        from kul_ocr.entrypoints.celery_app import app

        _ = app.control.revoke(task_id, terminate=True)
