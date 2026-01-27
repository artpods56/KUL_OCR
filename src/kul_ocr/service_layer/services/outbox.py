from datetime import datetime, timedelta
from typing import Sequence

from kul_ocr.domain import structs
from kul_ocr.domain.protocols import TaskRunner
from kul_ocr.service_layer.uow import AbstractUnitOfWork

from kul_ocr.utils.logger import get_logger

logger = get_logger(__name__)


def relay_pending_outbox_entries(
    task_runner: TaskRunner,
    uow: AbstractUnitOfWork,
    batch_size: int = 100,
) -> Sequence[structs.OutboxEntryDTO]:
    """Process pending outbox entries and schedule corresponding tasks.

    Fetches pending outbox entries, schedules Celery tasks for each, and marks
    them as relayed. Processes entries in batches for efficiency.

    Args:
        task_runner: Task runner for scheduling Celery tasks.
        uow: Unit of Work instance.
        batch_size: Maximum number of entries to process in one batch.

    Returns:
        Number of entries successfully relayed.
    """

    relayed_entry_ids: set[str] = set()

    with uow:
        pending_entries = uow.outbox.list_pending(limit=batch_size)

        for entry in pending_entries:
            try:
                task_runner.schedule_task(entry)
                entry.mark_as_relayed()
                relayed_entry_ids.add(entry.id)

                logger.info(
                    "Relayed outbox entry",
                    entry_id=entry.id,
                    job_id=entry.aggregate_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to relay outbox entry",
                    entry_id=entry.id,
                    job_id=entry.aggregate_id,
                    error=str(e),
                    exc_info=True,
                )

        uow.commit()

        return [
            structs.OutboxEntryDTO.from_domain(entry)
            for entry in pending_entries
            if entry.id in relayed_entry_ids
        ]


def cleanup_old_outbox_entries(
    uow: AbstractUnitOfWork,
    retention_hours: int = 24,
) -> int:
    """Delete old relayed outbox entries.

    Removes outbox entries that have been relayed and are older than the
    retention period to prevent unbounded table growth.

    Args:
        uow: Unit of Work instance.
        retention_hours: Number of hours to retain relayed entries.

    Returns:
        Number of entries deleted.
    """
    with uow:
        cutoff = datetime.now() - timedelta(hours=retention_hours)
        deleted_count = uow.outbox.delete_relayed_older_than(cutoff)
        uow.commit()

        if deleted_count > 0:
            logger.info(
                "Cleaned up old outbox entries",
                deleted_count=deleted_count,
                retention_hours=retention_hours,
            )

        return deleted_count
