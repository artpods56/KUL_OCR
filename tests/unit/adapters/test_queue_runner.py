"""Unit tests for CeleryTaskRunner."""

import pytest
from unittest.mock import patch


from core.adapters.queue.runner import CeleryTaskRunner
from core.domain import model, enums
from tests.fakes.celery_app import FakeCeleryApp
from tests.factories import (
    generate_document_upload_outbox_entry,
    generate_job_scheduling_outbox_entry,
    generate_outbox_entries,
)


class TestCeleryTaskRunner:
    """Test suite for CeleryTaskRunner."""

    @pytest.fixture
    def fake_celery_app(self) -> FakeCeleryApp:
        """Provide a fake Celery app for testing."""
        return FakeCeleryApp()

    @pytest.fixture
    def runner(self) -> CeleryTaskRunner:
        """Provide a CeleryTaskRunner."""
        return CeleryTaskRunner()

    def _get_celery_app(self, runner: CeleryTaskRunner, fake_app: FakeCeleryApp):
        """Helper to patch Celery app import."""

        def mock_import():
            return fake_app

        return mock_import

    @pytest.fixture
    def job_scheduling_entry(self) -> model.OutboxEntry:
        """Provide a JOB_SCHEDULING outbox entry."""
        return generate_job_scheduling_outbox_entry()

    @pytest.fixture
    def document_upload_entry(self) -> model.OutboxEntry:
        """Provide a DOCUMENT_UPLOAD outbox entry."""
        return generate_document_upload_outbox_entry()


class TestScheduleTask(TestCeleryTaskRunner):
    """Test CeleryTaskRunner.schedule_task() method."""

    def test_schedule_job_scheduling_task_success(
        self, fake_celery_app: FakeCeleryApp, job_scheduling_entry: model.OutboxEntry
    ):
        """Test successful scheduling of JOB_SCHEDULING task."""
        # Create runner and patch Celery app
        runner = CeleryTaskRunner()

        with patch("worker.main.app", fake_celery_app):
            # Schedule the task
            runner.schedule_task(job_scheduling_entry)

        # Verify task was sent
        assert len(fake_celery_app.sent_tasks) == 1
        sent_task = fake_celery_app.sent_tasks[0]

        assert sent_task.task_name == "worker.tasks.process_job"
        assert sent_task.task_id == job_scheduling_entry.id
        assert sent_task.kwargs == job_scheduling_entry.payload
        assert sent_task.args == ()

    def test_schedule_document_upload_task_success(
        self, fake_celery_app: FakeCeleryApp, document_upload_entry: model.OutboxEntry
    ):
        """Test successful scheduling of DOCUMENT_UPLOAD task."""
        runner = CeleryTaskRunner()

        with patch("worker.main.app", fake_celery_app):
            runner.schedule_task(document_upload_entry)

        # Verify task was sent
        assert len(fake_celery_app.sent_tasks) == 1
        sent_task = fake_celery_app.sent_tasks[0]

        assert sent_task.task_name == "worker.tasks.upload_document"
        assert sent_task.task_id == document_upload_entry.id
        assert sent_task.kwargs == document_upload_entry.payload

    def test_schedule_task_with_unknown_event_type(
        self, fake_celery_app: FakeCeleryApp
    ):
        """Test scheduling with unknown event type raises ValueError."""
        # Create entry with unknown event type (we'll simulate this)
        runner = CeleryTaskRunner()

        # Create an entry that would have an unmapped event type
        # We need to mock TASK_NAMES temporarily to simulate missing mapping
        original_task_names = model.TASK_NAMES.copy()

        try:
            # Remove the mapping temporarily
            del model.TASK_NAMES[enums.OutboxEventType.JOB_SCHEDULING]

            entry = generate_document_upload_outbox_entry()

            entry.event_type = enums.OutboxEventType.JOB_SCHEDULING

            with patch("worker.main.app", fake_celery_app):
                with pytest.raises(ValueError) as exc_info:
                    runner.schedule_task(entry)

                assert "No task configured for event type" in str(exc_info.value)
                assert "OutboxEventType.JOB_SCHEDULING" in str(exc_info.value)

        finally:
            model.TASK_NAMES.update(original_task_names)

        assert len(fake_celery_app.sent_tasks) == 0

    def test_schedule_task_celery_send_task_fails(
        self, fake_celery_app: FakeCeleryApp, job_scheduling_entry: model.OutboxEntry
    ):
        """Test behavior when Celery send_task fails."""
        runner = CeleryTaskRunner()

        # Configure fake app to fail
        fake_celery_app.should_fail_send_task = True

        with patch("worker.main.app", fake_celery_app):
            with pytest.raises(RuntimeError) as exc_info:
                runner.schedule_task(job_scheduling_entry)

            assert "Failed to send task" in str(exc_info.value)
            assert "process_job" in str(exc_info.value)

    @pytest.fixture
    def test_schedule_task_preserves_payload_data(
        self, fake_celery_app: FakeCeleryApp, job_scheduling_entry: model.OutboxEntry
    ):
        """Test that payload data is preserved exactly when scheduling."""

        runner = CeleryTaskRunner()

        with patch("worker.main.app", fake_celery_app):
            runner.schedule_task(job_scheduling_entry)

        sent_task = fake_celery_app.sent_tasks[0]

        # Verify all payload data is preserved
        assert sent_task.kwargs == job_scheduling_entry.payload
        assert sent_task.task_id == job_scheduling_entry.id

    @pytest.mark.parametrize(
        "event_type",
        [enums.OutboxEventType.JOB_SCHEDULING, enums.OutboxEventType.DOCUMENT_UPLOAD],
    )
    def test_schedule_multiple_tasks(
        self, fake_celery_app: FakeCeleryApp, event_type: enums.OutboxEventType
    ):
        """Test scheduling multiple tasks of different types."""
        runner = CeleryTaskRunner()

        entries = generate_outbox_entries(event_type=event_type)

        with patch("worker.main.app", fake_celery_app):
            _ = [runner.schedule_task(entry) for entry in entries]

        assert len(fake_celery_app.sent_tasks) == len(entries)

        for entry, sent_task in zip(entries, fake_celery_app.sent_tasks):
            assert entry.payload == sent_task.kwargs
            assert entry.id == sent_task.task_id


class TestRevokeTask(TestCeleryTaskRunner):
    """Test CeleryTaskRunner.revoke_task() method."""

    def test_revoke_task_success(self, fake_celery_app: FakeCeleryApp):
        """Test successful task revocation."""
        runner = CeleryTaskRunner()
        task_id = "task-to-revoke-123"

        with patch("worker.main.app", fake_celery_app):
            runner.revoke_task(task_id)

        # Verify task was revoked
        assert len(fake_celery_app.control.revoked_tasks) == 1
        revoked_task = fake_celery_app.control.revoked_tasks[0]

        assert revoked_task.task_id == task_id
        assert revoked_task.terminate is True

    def test_revoke_multiple_tasks(self, fake_celery_app: FakeCeleryApp):
        """Test revoking multiple tasks."""
        runner = CeleryTaskRunner()
        task_ids = ["task-1", "task-2", "task-3"]

        with patch("worker.main.app", fake_celery_app):
            for task_id in task_ids:
                runner.revoke_task(task_id)

        # Verify all tasks were revoked
        assert len(fake_celery_app.control.revoked_tasks) == 3
        revoked_ids = [t.task_id for t in fake_celery_app.control.revoked_tasks]
        assert set(revoked_ids) == set(task_ids)

        # All should have terminate=True
        for revoked in fake_celery_app.control.revoked_tasks:
            assert revoked.terminate is True

    def test_revoke_task_celery_revoke_fails(self, fake_celery_app: FakeCeleryApp):
        """Test behavior when Celery revoke fails."""
        runner = CeleryTaskRunner()
        task_id = "failing-task"

        # Configure fake control to fail
        fake_celery_app.control.should_fail_revoke = True

        with patch("worker.main.app", fake_celery_app):
            with pytest.raises(RuntimeError) as exc_info:
                runner.revoke_task(task_id)

            assert "Failed to revoke task" in str(exc_info.value)
            assert task_id in str(exc_info.value)

    def test_revoke_task_specific_task_fails(self, fake_celery_app: FakeCeleryApp):
        """Test revoking specific tasks that are configured to fail."""
        runner = CeleryTaskRunner()

        # Configure specific task to fail
        failing_task_id = "will-fail"
        success_task_id = "will-succeed"
        fake_celery_app.control.fail_revoke_for_task_ids.add(failing_task_id)

        with patch("worker.main.app", fake_celery_app):
            # This should fail
            with pytest.raises(RuntimeError):
                runner.revoke_task(failing_task_id)

            # This should succeed
            runner.revoke_task(success_task_id)

        # Verify only the successful task was recorded
        assert len(fake_celery_app.control.revoked_tasks) == 1
        assert fake_celery_app.control.revoked_tasks[0].task_id == success_task_id


class TestCeleryTaskRunnerIntegration(TestCeleryTaskRunner):
    """Integration tests for CeleryTaskRunner functionality."""

    def test_schedule_and_revoke_task_workflow(
        self, fake_celery_app: FakeCeleryApp, job_scheduling_entry: model.OutboxEntry
    ):
        """Test complete workflow: schedule a task then revoke it."""
        runner = CeleryTaskRunner()

        with patch("worker.main.app", fake_celery_app):
            # Schedule task
            runner.schedule_task(job_scheduling_entry)

            # Get the task ID that was used
            sent_task = fake_celery_app.sent_tasks[0]
            task_id = sent_task.task_id
            assert task_id is not None  # Ensure it's not None for type checker

            # Revoke the task
            runner.revoke_task(task_id)

        # Verify both operations recorded
        assert len(fake_celery_app.sent_tasks) == 1
        assert len(fake_celery_app.control.revoked_tasks) == 1

        # Verify IDs match
        assert fake_celery_app.control.revoked_tasks[0].task_id == task_id

    def test_error_resilience(self, fake_celery_app: FakeCeleryApp):
        """Test error resilience - failures don't affect subsequent operations."""
        runner = CeleryTaskRunner()

        failing_task_name = "worker.tasks.process_job"

        fake_celery_app.fail_send_task_for_names.add(failing_task_name)

        job_entry = generate_job_scheduling_outbox_entry()

        doc_entry = generate_document_upload_outbox_entry()

        with patch("worker.main.app", fake_celery_app):
            with pytest.raises(RuntimeError):
                runner.schedule_task(job_entry)

            runner.schedule_task(doc_entry)

        assert len(fake_celery_app.sent_tasks) == 1
        assert fake_celery_app.sent_tasks[0].task_name == "worker.tasks.upload_document"
