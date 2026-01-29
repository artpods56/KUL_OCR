import pytest
from datetime import datetime

from core.domain import exceptions
from core.domain.model import OutboxEntry
from core.domain.enums import OutboxEventType
from core.service_layer.helpers import generate_id


class TestOutboxEntry:
    def test_outbox_entry_initialization(self):
        entry = OutboxEntry(
            id="entry-1",
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id="job-1",
            payload={"job_id": "job-1", "task_id": "task-1"},
        )

        assert entry.id == "entry-1"
        assert entry.event_type == OutboxEventType.JOB_SCHEDULING
        assert entry.aggregate_id == "job-1"
        assert entry.payload == {"job_id": "job-1", "task_id": "task-1"}
        assert entry.created_at is not None
        assert entry.relayed_at is None

    def test_outbox_entry_is_relayed_false_initially(self):
        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},
        )

        assert entry.is_relayed is False

    def test_outbox_entry_mark_as_relayed(self):
        entry = OutboxEntry(
            id=generate_id(),
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},
        )

        assert entry.is_relayed is False
        entry.mark_as_relayed()

        assert entry.is_relayed is True
        assert entry.relayed_at is not None
        assert isinstance(entry.relayed_at, datetime)

    def test_outbox_entry_cannot_relay_twice(self):
        entry = OutboxEntry(
            id="entry-double-relay",
            event_type=OutboxEventType.JOB_SCHEDULING,
            aggregate_id=generate_id(),
            payload={},
        )

        entry.mark_as_relayed()

        with pytest.raises(exceptions.OutboxEntryAlreadyRelayedError) as excinfo:
            entry.mark_as_relayed()

        assert "entry-double-relay" in str(excinfo.value)

    def test_outbox_entry_event_type_enum(self):
        assert OutboxEventType.JOB_SCHEDULING.value == "job_scheduling"
        assert OutboxEventType.DOCUMENT_UPLOAD.value == "document_upload"
