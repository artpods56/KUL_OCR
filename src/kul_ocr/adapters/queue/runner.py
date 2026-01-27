from typing import override

from kul_ocr.domain import model, protocols


class CeleryTaskRunner(protocols.TaskRunner):
    @override
    def schedule_task(self, entry: model.OutboxEntry) -> None:
        from kul_ocr.entrypoints.celery_app import app

        task_name = model.TASK_NAMES.get(entry.event_type)
        if task_name is None:
            raise ValueError(f"No task configured for event type: {entry.event_type}")
        match entry.event_type:
            case model.OutboxEventType.OCR_JOB_SCHEDULED:
                _ = app.send_task(
                    task_name,
                    task_id=entry.aggregate_id,
                    kwargs={"job_id": entry.payload["job_id"]},
                )

    @override
    def revoke_task(self, task_id: str) -> None:
        from kul_ocr.entrypoints.celery_app import app

        _ = app.control.revoke(task_id, terminate=True)
