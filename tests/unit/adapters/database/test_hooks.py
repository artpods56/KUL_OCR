from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import orm

from core.adapters.database.hooks import CollectAndScheduleTasksHook
from core.domain import dto
from tests import factories
from tests.fakes.task_runner import FakeTaskRunner


class FakeSession(orm.Session):
    """Fake session for testing hooks without a real database connection."""

    def __init__(self) -> None:
        # Don't call super().__init__() - we don't need a real connection
        self._new: list[Any] = []
        self.info: dict[str, Any] = {}

    @property
    def new(self) -> list[Any]:
        return self._new

    def add_new(self, *objects: Any) -> None:
        """Add objects to the new collection (simulates session.add)."""
        self._new.extend(objects)


class TestCollectAndScheduleTasksHook:
    @pytest.fixture
    def task_runner(self) -> FakeTaskRunner:
        return FakeTaskRunner()

    @pytest.fixture
    def hook(self, task_runner: FakeTaskRunner) -> CollectAndScheduleTasksHook:
        return CollectAndScheduleTasksHook(task_runner)

    @pytest.fixture
    def fake_session(self) -> FakeSession:
        return FakeSession()


class TestCall(TestCollectAndScheduleTasksHook):
    @patch("sqlalchemy.event.listen")
    def test_registers_before_commit_listener(
        self,
        mock_listen: MagicMock,
        hook: CollectAndScheduleTasksHook,
    ):
        hook(FakeSession)

        mock_listen.assert_any_call(FakeSession, "before_commit", hook.pre_commit)

    @patch("sqlalchemy.event.listen")
    def test_registers_after_commit_listener(
        self,
        mock_listen: MagicMock,
        hook: CollectAndScheduleTasksHook,
    ):
        hook(FakeSession)

        mock_listen.assert_any_call(FakeSession, "after_commit", hook.post_commit)


class TestPreCommit(TestCollectAndScheduleTasksHook):
    def test_collects_outbox_entries_from_session_new(
        self,
        fake_session: FakeSession,
    ):
        outbox_entry = factories.generate_job_scheduling_outbox_entry()
        fake_session.add_new(outbox_entry)

        CollectAndScheduleTasksHook.pre_commit(fake_session)

        tasks = fake_session.info["outbox_tasks"]
        assert len(tasks) == 1
        assert isinstance(tasks[0], dto.OutboxEntryDTO)
        assert tasks[0].id == outbox_entry.id

    def test_ignores_non_outbox_entry_objects(
        self,
        fake_session: FakeSession,
    ):
        outbox_entry = factories.generate_job_scheduling_outbox_entry()
        job = factories.generate_ocr_job()
        fake_session.add_new(outbox_entry, job)

        CollectAndScheduleTasksHook.pre_commit(fake_session)

        tasks = fake_session.info["outbox_tasks"]
        assert len(tasks) == 1
        assert tasks[0].id == outbox_entry.id

    def test_handles_empty_session_new(self, fake_session: FakeSession):
        CollectAndScheduleTasksHook.pre_commit(fake_session)

        assert fake_session.info["outbox_tasks"] == []

    def test_collects_multiple_outbox_entries(self, fake_session: FakeSession):
        entry1 = factories.generate_job_scheduling_outbox_entry()
        entry2 = factories.generate_document_upload_outbox_entry()
        fake_session.add_new(entry1, entry2)

        CollectAndScheduleTasksHook.pre_commit(fake_session)

        tasks = fake_session.info["outbox_tasks"]
        assert len(tasks) == 2
        task_ids = {t.id for t in tasks}
        assert task_ids == {entry1.id, entry2.id}


class TestPostCommit(TestCollectAndScheduleTasksHook):
    def test_schedules_tasks_for_each_entry(
        self,
        task_runner: FakeTaskRunner,
        hook: CollectAndScheduleTasksHook,
        fake_session: FakeSession,
    ):
        outbox_entry = factories.generate_job_scheduling_outbox_entry()
        entry_dto = dto.OutboxEntryDTO.from_domain(outbox_entry)
        fake_session.info["outbox_tasks"] = [entry_dto]

        hook.post_commit(fake_session)

        assert len(task_runner.scheduled_tasks) == 1
        assert task_runner.was_task_scheduled(outbox_entry.id)

    def test_pops_tasks_from_session_info(
        self,
        hook: CollectAndScheduleTasksHook,
        fake_session: FakeSession,
    ):
        outbox_entry = factories.generate_job_scheduling_outbox_entry()
        entry_dto = dto.OutboxEntryDTO.from_domain(outbox_entry)
        fake_session.info["outbox_tasks"] = [entry_dto]

        hook.post_commit(fake_session)

        assert "outbox_tasks" not in fake_session.info

    def test_handles_empty_task_list(
        self,
        task_runner: FakeTaskRunner,
        hook: CollectAndScheduleTasksHook,
        fake_session: FakeSession,
    ):
        fake_session.info["outbox_tasks"] = []

        hook.post_commit(fake_session)

        assert len(task_runner.scheduled_tasks) == 0

    def test_handles_missing_outbox_tasks_key(
        self,
        task_runner: FakeTaskRunner,
        hook: CollectAndScheduleTasksHook,
        fake_session: FakeSession,
    ):
        # info dict has no "outbox_tasks" key

        hook.post_commit(fake_session)

        assert len(task_runner.scheduled_tasks) == 0

    def test_schedules_multiple_tasks(
        self,
        task_runner: FakeTaskRunner,
        hook: CollectAndScheduleTasksHook,
        fake_session: FakeSession,
    ):
        entry1 = factories.generate_job_scheduling_outbox_entry()
        entry2 = factories.generate_job_scheduling_outbox_entry()
        dtos = [
            dto.OutboxEntryDTO.from_domain(entry1),
            dto.OutboxEntryDTO.from_domain(entry2),
        ]
        fake_session.info["outbox_tasks"] = dtos

        hook.post_commit(fake_session)

        assert len(task_runner.scheduled_tasks) == 2
        assert task_runner.was_task_scheduled(entry1.id)
        assert task_runner.was_task_scheduled(entry2.id)
