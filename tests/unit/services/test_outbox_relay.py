from datetime import datetime, timedelta
from typing import cast


from backend.jobs import service as jobs_service
from backend.outbox import service
from core.domain.enums import JobStatus, OutboxEventType
from tests.factories import (
    generate_document_without_file,
    generate_job_scheduling_outbox_entry,
    generate_ocr_job,
    generate_outbox_entries,
)
from tests.fakes.repositories import FakeOutboxRepository
from tests.fakes.task_runner import FakeTaskRunner
from tests.fakes.uow import FakeUnitOfWork


class TestStartOcrJobProcessingWithOutbox:
    def test_start_ocr_job_processing_creates_outbox_entry(self, uow: FakeUnitOfWork):
        document = generate_document_without_file()
        job = generate_ocr_job(document_id=document.id)

        uow.documents.add(document)
        uow.jobs.add(job)

        result = jobs_service.start_ocr_job_processing(job.id, uow)

        assert result.status == JobStatus.PROCESSING.value
        outbox_repo = cast(FakeOutboxRepository, uow.outbox)
        outbox_entry = outbox_repo.added[0]
        assert outbox_entry.event_type == OutboxEventType.JOB_SCHEDULING
        assert outbox_entry.aggregate_id == job.id
        assert outbox_entry.payload["type"] == "job_processing"
        assert outbox_entry.payload["job_id"] == job.id
        assert "job_id" in outbox_entry.payload

    def test_start_ocr_job_processing_assigns_task_id(self, uow: FakeUnitOfWork):
        document = generate_document_without_file()
        job = generate_ocr_job(document_id=document.id)

        uow.documents.add(document)
        uow.jobs.add(job)

        _ = jobs_service.start_ocr_job_processing(job.id, uow)

        updated_job = uow.jobs.get(job.id)
        assert updated_job is not None
        assert updated_job.task_id is not None

        outbox_repo = cast(FakeOutboxRepository, uow.outbox)
        outbox_entry = outbox_repo.added[0]
        assert outbox_entry.payload["type"] == "job_processing"
        assert outbox_entry.payload["job_id"] == updated_job.id

    def test_start_ocr_job_commits_transaction(self, uow: FakeUnitOfWork):
        document = generate_document_without_file()
        job = generate_ocr_job(document_id=document.id)

        uow.documents.add(document)
        uow.jobs.add(job)

        _ = jobs_service.start_ocr_job_processing(job.id, uow)

        assert uow.committed is True


class TestRelayPendingOutboxEntries:
    def test_relay_schedules_celery_tasks(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        entry = generate_job_scheduling_outbox_entry()
        uow.outbox.add(entry)

        relayed_entries = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert len(relayed_entries) == 1
        assert task_runner.was_task_scheduled(entry.id)
        scheduled = task_runner.get_scheduled_task(entry.id)
        assert scheduled is not None
        assert scheduled.id == entry.id

    def test_relay_marks_entries_as_relayed(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        entry = generate_job_scheduling_outbox_entry()
        uow.outbox.add(entry)

        _ = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert entry.is_relayed is True
        assert entry.relayed_at is not None

    def test_relay_commits_transaction(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        entry = generate_job_scheduling_outbox_entry()
        uow.outbox.add(entry)

        _ = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert uow.committed is True

    def test_relay_respects_batch_size(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        for entry in generate_outbox_entries(count=5):
            uow.outbox.add(entry)

        relayed_entries = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=2
        )

        assert len(relayed_entries) == 2
        assert len(task_runner.scheduled_tasks) == 2

    def test_relay_skips_already_relayed_entries(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        entry = generate_job_scheduling_outbox_entry()
        entry.mark_as_relayed()
        uow.outbox.add(entry)

        relayed_entries = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert len(relayed_entries) == 0
        assert len(task_runner.scheduled_tasks) == 0

    def test_relay_handles_empty_outbox(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        relayed_entries = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert len(relayed_entries) == 0

    def test_relay_skips_entries_with_invalid_payload(self, uow: FakeUnitOfWork):
        task_runner = FakeTaskRunner()

        entry = generate_job_scheduling_outbox_entry()
        entry.payload = {}  # pyright: ignore[reportAttributeAccessIssue]
        uow.outbox.add(entry)

        relayed_entries = service.relay_pending_outbox_entries(
            task_runner=task_runner, uow=uow, batch_size=100
        )

        assert len(relayed_entries) == 0
        assert len(task_runner.scheduled_tasks) == 0


class TestCleanupOldOutboxEntries:
    def test_cleanup_deletes_old_relayed_entries(self, uow: FakeUnitOfWork):
        entry = generate_job_scheduling_outbox_entry()
        entry.mark_as_relayed()
        entry.relayed_at = datetime.now() - timedelta(hours=48)
        uow.outbox.add(entry)

        deleted_count = service.cleanup_old_outbox_entries(uow=uow, retention_hours=24)

        assert deleted_count == 1
        assert uow.outbox.get(entry.id) is None

    def test_cleanup_keeps_recent_relayed_entries(self, uow: FakeUnitOfWork):
        entry = generate_job_scheduling_outbox_entry()
        entry.mark_as_relayed()
        uow.outbox.add(entry)

        deleted_count = service.cleanup_old_outbox_entries(uow=uow, retention_hours=24)

        assert deleted_count == 0
        assert uow.outbox.get(entry.id) is not None

    def test_cleanup_keeps_pending_entries(self, uow: FakeUnitOfWork):
        entry = generate_job_scheduling_outbox_entry()
        entry.created_at = datetime.now() - timedelta(hours=48)
        uow.outbox.add(entry)

        deleted_count = service.cleanup_old_outbox_entries(uow=uow, retention_hours=24)

        assert deleted_count == 0
        assert uow.outbox.get(entry.id) is not None

    def test_cleanup_commits_transaction(self, uow: FakeUnitOfWork):
        deleted_count = service.cleanup_old_outbox_entries(uow=uow, retention_hours=24)

        assert deleted_count == 0
        assert uow.committed is True
