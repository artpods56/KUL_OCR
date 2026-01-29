from datetime import datetime, timedelta

import core.service_layer.services.jobs
import core.service_layer.services.outbox
from core.domain.model import OutboxEntry
from core.domain.enums import JobStatus, OutboxEventType
from core.service_layer.helpers import generate_id
from tests.factories import generate_ocr_job, generate_document_without_file
from tests.fakes.task_runner import FakeTaskRunner
from tests.fakes.uow import FakeUnitOfWork


class TestStartOcrJobProcessingWithOutbox:
    def test_start_ocr_job_processing_creates_outbox_entry(self):
        uow = FakeUnitOfWork()
        document = generate_document_without_file()
        job = generate_ocr_job(document_id=document.id)

        uow.documents.add(document)
        uow.jobs.add(job)

        result = core.service_layer.services.jobs.start_ocr_job_processing(job.id, uow)

        assert result.status == JobStatus.PROCESSING.value
        assert len(uow.outbox.added) == 1

        outbox_entry = uow.outbox.added[0]
        assert outbox_entry.event_type == OutboxEventType.JOB_SCHEDULING
        assert outbox_entry.aggregate_id == job.id
        assert outbox_entry.payload["job_id"] == job.id
        assert "job_id" in outbox_entry.payload

    def test_start_ocr_job_processing_assigns_task_id(self):
        uow = FakeUnitOfWork()
        document = generate_document_without_file()
        job = generate_ocr_job(document_id=document.id)

        uow.documents.add(document)
        uow.jobs.add(job)

        _ = core.service_layer.services.jobs.start_ocr_job_processing(job.id, uow)

        # Verify task_id was assigned to job
        updated_job = uow.jobs.get(job.id)
        assert updated_job is not None
        assert updated_job.task_id is not None

        # Verify task_id matches outbox entry
        outbox_entry = uow.outbox.added[0]
        assert outbox_entry.payload["job_id"] == updated_job.id

    def test_start_ocr_job_commits_transaction(self):
        uow = FakeUnitOfWork()
        document = generate_document_without_file()
        job = generate_ocr_job(document_id=document.id)

        uow.documents.add(document)
        uow.jobs.add(job)

        _ = core.service_layer.services.jobs.start_ocr_job_processing(job.id, uow)

        assert uow.committed is True


class TestRelayPendingOutboxEntries:
    def test_relay_schedules_celery_tasks(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        # Create pending outbox entries
        job_id = generate_id()
        task_id = generate_id()
        document_id = generate_id()

        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=job_id,
            payload={
                "job_id": job_id,
                "task_id": task_id,
                "document_id": document_id,
            },
        )
        uow.outbox.add(entry)

        relayed_entries = (
            core.service_layer.services.outbox.relay_pending_outbox_entries(
                task_runner=task_runner, uow=uow, batch_size=100
            )
        )

        assert len(relayed_entries) == 1
        assert task_runner.was_task_scheduled(job_id)

        scheduled = task_runner.get_scheduled_task(job_id)
        assert scheduled is not None
        assert scheduled.task_id == job_id

    def test_relay_marks_entries_as_relayed(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={
                "job_id": generate_id(),
                "task_id": generate_id(),
                "document_id": generate_id(),
            },
        )
        uow.outbox.add(entry)

        _ = core.service_layer.services.outbox.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert entry.is_relayed is True
        assert entry.relayed_at is not None

    def test_relay_commits_transaction(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={
                "job_id": generate_id(),
                "task_id": generate_id(),
                "document_id": generate_id(),
            },
        )
        uow.outbox.add(entry)

        _ = core.service_layer.services.outbox.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert uow.committed is True

    def test_relay_respects_batch_size(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        # Create 5 entries
        for _ in range(5):
            entry = OutboxEntry(
                id=generate_id(),
                event_type=OutboxEventType.JOB_SCHEDULING,
                aggregate_id=generate_id(),
                payload={
                    "job_id": generate_id(),
                    "task_id": generate_id(),
                    "document_id": generate_id(),
                },
            )
            uow.outbox.add(entry)

        # Only relay 2
        relayed_entries = (
            core.service_layer.services.outbox.relay_pending_outbox_entries(
                task_runner=task_runner, uow=uow, batch_size=2
            )
        )

        assert len(relayed_entries) == 2
        assert len(task_runner.scheduled_tasks) == 2

    def test_relay_skips_already_relayed_entries(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        # Create and relay an entry
        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={
                "job_id": generate_id(),
                "task_id": generate_id(),
                "document_id": generate_id(),
            },
        )
        entry.mark_as_relayed()
        uow.outbox.add(entry)

        relayed_entries = (
            core.service_layer.services.outbox.relay_pending_outbox_entries(
                task_runner=task_runner, uow=uow, batch_size=100
            )
        )

        assert len(relayed_entries) == 0
        assert len(task_runner.scheduled_tasks) == 0

    def test_relay_handles_empty_outbox(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        relayed_entries = (
            core.service_layer.services.outbox.relay_pending_outbox_entries(
                task_runner=task_runner, uow=uow, batch_size=100
            )
        )

        assert len(relayed_entries) == 0

    def test_relay_skips_entries_with_invalid_payload(self):
        uow = FakeUnitOfWork()
        task_runner = FakeTaskRunner()

        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},  # Missing job_id and task_id
        )
        uow.outbox.add(entry)

        relayed_entries = (
            core.service_layer.services.outbox.relay_pending_outbox_entries(
                task_runner=task_runner, uow=uow, batch_size=100
            )
        )

        assert len(relayed_entries) == 0
        assert len(task_runner.scheduled_tasks) == 0


class TestCleanupOldOutboxEntries:
    def test_cleanup_deletes_old_relayed_entries(self):
        uow = FakeUnitOfWork()

        # Create an old relayed entry
        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},
        )
        entry.mark_as_relayed()
        # Manually set relayed_at to an old time
        entry.relayed_at = datetime.now() - timedelta(hours=48)
        uow.outbox.add(entry)

        deleted_count = core.service_layer.services.outbox.cleanup_old_outbox_entries(
            uow=uow, retention_hours=24
        )

        assert deleted_count == 1
        assert uow.outbox.get(entry.id) is None

    def test_cleanup_keeps_recent_relayed_entries(self):
        uow = FakeUnitOfWork()

        # Create a recently relayed entry
        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},
        )
        entry.mark_as_relayed()
        # relayed_at is set to now by mark_as_relayed()
        uow.outbox.add(entry)

        deleted_count = core.service_layer.services.outbox.cleanup_old_outbox_entries(
            uow=uow, retention_hours=24
        )

        assert deleted_count == 0
        assert uow.outbox.get(entry.id) is not None

    def test_cleanup_keeps_pending_entries(self):
        uow = FakeUnitOfWork()

        # Create an old pending (not relayed) entry
        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},
            created_at=datetime.now() - timedelta(hours=48),
        )
        uow.outbox.add(entry)

        deleted_count = core.service_layer.services.outbox.cleanup_old_outbox_entries(
            uow=uow, retention_hours=24
        )

        assert deleted_count == 0
        assert uow.outbox.get(entry.id) is not None

    def test_cleanup_commits_transaction(self):
        uow = FakeUnitOfWork()

        deleted_count = core.service_layer.services.outbox.cleanup_old_outbox_entries(
            uow=uow, retention_hours=24
        )

        assert deleted_count == 0
        assert uow.committed is True
