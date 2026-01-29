from dataclasses import dataclass
from typing import final, override

from core.domain import model, enums
from core.domain.protocols import TaskRunner


@dataclass
class ScheduledTask:
    """Record of a scheduled task."""

    job_id: str
    task_id: str


@final
class FakeTaskRunner(TaskRunner):
    """Fake task runner for testing."""

    def __init__(self):
        self.scheduled_tasks: list[ScheduledTask] = []
        self.revoked_tasks: list[str] = []
        self.should_fail: bool = False
        self.should_fail_revoke: bool = False
        self.fail_revoke_for_task_ids: set[str] = set()

    @override
    def schedule_task(self, entry: model.OutboxEntry) -> None:
        match entry.event_type:
            case enums.OutboxEventType.JOB_SCHEDULING:
                if self.should_fail:
                    raise RuntimeError("FakeTaskRunner configured to fail")
                job_id = entry.payload.get("job_id")
                task_id = entry.aggregate_id
                if job_id is not None:
                    self.scheduled_tasks.append(
                        ScheduledTask(job_id=job_id, task_id=task_id)
                    )
                else:
                    raise ValueError(
                        f"Cannot relay outbox entry {entry.id}: "
                        f"missing 'job_id' in payload"
                    )

    @override
    def revoke_task(self, task_id: str) -> None:
        if self.should_fail_revoke or task_id in self.fail_revoke_for_task_ids:
            raise RuntimeError(f"Failed to revoke task {task_id}")
        self.revoked_tasks.append(task_id)

    def get_scheduled_task(self, job_id: str) -> ScheduledTask | None:
        """Get the scheduled task for a job ID."""
        return next(
            (t for t in self.scheduled_tasks if t.job_id == job_id),
            None,
        )

    def was_task_scheduled(self, job_id: str) -> bool:
        """Check if a task was scheduled for the given job ID."""
        return any(t.job_id == job_id for t in self.scheduled_tasks)

    def clear(self) -> None:
        """Clear all recorded tasks."""
        self.scheduled_tasks.clear()
        self.revoked_tasks.clear()
