"""Fake Celery app implementation for testing CeleryTaskRunner."""

from dataclasses import dataclass, field
from typing import Any, final


@dataclass
class SentTask:
    """Record of a task sent via Celery."""

    task_name: str
    task_id: str | None
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class RevokedTask:
    """Record of a revoked task."""

    task_id: str
    terminate: bool = False


@final
class FakeCeleryControl:
    """Fake Celery control interface."""

    def __init__(self):
        self.revoked_tasks: list[RevokedTask] = []
        self.should_fail_revoke: bool = False
        self.fail_revoke_for_task_ids: set[str] = set()

    def revoke(self, task_id: str, terminate: bool = False) -> None:
        """Revoke a task by ID."""
        if self.should_fail_revoke or task_id in self.fail_revoke_for_task_ids:
            raise RuntimeError(f"Failed to revoke task {task_id}")

        self.revoked_tasks.append(RevokedTask(task_id=task_id, terminate=terminate))

    def was_task_revoked(self, task_id: str) -> bool:
        """Check if a task was revoked."""
        return any(t.task_id == task_id for t in self.revoked_tasks)

    def get_revoked_task(self, task_id: str) -> RevokedTask | None:
        """Get revoked task details by ID."""
        return next(
            (t for t in self.revoked_tasks if t.task_id == task_id),
            None,
        )

    def clear(self) -> None:
        """Clear all recorded revoked tasks."""
        self.revoked_tasks.clear()


@final
class FakeCeleryApp:
    """Fake Celery application for testing."""

    def __init__(self):
        self.sent_tasks: list[SentTask] = []
        self.control = FakeCeleryControl()
        self.should_fail_send_task: bool = False
        self.fail_send_task_for_names: set[str] = set()

    def send_task(
        self,
        task_name: str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        task_id: str | None = None,
        **options: Any,
    ) -> None:
        """Send a task to be executed."""
        if kwargs is None:
            kwargs = {}

        if self.should_fail_send_task or task_name in self.fail_send_task_for_names:
            raise RuntimeError(f"Failed to send task {task_name}")

        self.sent_tasks.append(
            SentTask(
                task_name=task_name,
                task_id=task_id,
                args=args,
                kwargs=kwargs,
            )
        )

    def get_sent_task(self, task_name: str) -> SentTask | None:
        """Get the first sent task by name."""
        return next(
            (t for t in self.sent_tasks if t.task_name == task_name),
            None,
        )

    def get_sent_tasks(self, task_name: str) -> list[SentTask]:
        """Get all sent tasks by name."""
        return [t for t in self.sent_tasks if t.task_name == task_name]

    def get_sent_task_by_id(self, task_id: str) -> SentTask | None:
        """Get sent task by ID."""
        return next(
            (t for t in self.sent_tasks if t.task_id == task_id),
            None,
        )

    def was_task_sent(self, task_name: str) -> bool:
        """Check if a task was sent."""
        return any(t.task_name == task_name for t in self.sent_tasks)

    def clear(self) -> None:
        """Clear all recorded tasks."""
        self.sent_tasks.clear()
        self.control.clear()
