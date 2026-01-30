from collections.abc import Sequence
from typing import Any, final, override

import msgspec
from sqlalchemy import (
    Column,
    DateTime,
    Dialect,
    Enum,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import registry, relationship
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.types import TypeDecorator

from core.domain import enums, model

mapper_registry = registry()

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("file_path", String(255), nullable=True),
    Column("file_type", Enum(enums.FileType), nullable=False),
    Column("uploaded_at", DateTime, nullable=True),
    Column("file_size_bytes", Integer, nullable=True),
    Column("original_filename", String(500), nullable=True),
)

ocr_jobs = Table(
    "ocr_jobs",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("document_id", String(255), ForeignKey("documents.id")),
    Column("created_at", DateTime),
    Column("error_message", String(255), nullable=True),
    Column("started_at", DateTime, nullable=True),
    Column("completed_at", DateTime, nullable=True),
    Column("task_id", String(255), nullable=True),
    Column("status", Enum(enums.JobStatus), nullable=False),
)


@final
class ProcessedPageType(TypeDecorator[Sequence[model.ProcessedPage] | None]):
    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
            self, value: Sequence[model.ProcessedPage] | None, dialect: Dialect
    ) -> str | None:
        """
        Encode a list of ProcessedPage objects into JSON string for storage.
        msgspec handles dataclass serialization natively.
        """
        if value is None:
            return None
        return msgspec.json.encode(list(value)).decode("utf-8")

    @override
    def process_result_value(
            self, value: str | None, dialect: Dialect
    ) -> Sequence[model.ProcessedPage] | None:
        """
        Decode a JSON string from the database to a list of ProcessedPage objects.
        msgspec.convert handles nested dataclass deserialization.
        """
        if value is None:
            return None

        data = msgspec.json.decode(value)
        if not isinstance(data, list):
            return None

        return [msgspec.convert(page_data, model.ProcessedPage) for page_data in data]


ocr_results = Table(
    "ocr_results",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("job_id", String(255), ForeignKey("ocr_jobs.id")),
    Column("creation_time", DateTime),
    Column("content", ProcessedPageType),
)


@final
class PayloadType(TypeDecorator[dict[str, Any] | None]):
    """TypeDecorator to serialize/deserialize outbox payload as JSON."""

    impl = Text
    cache_ok = True

    @override
    def process_bind_param(
            self, value: dict[str, Any] | None, dialect: Dialect
    ) -> str | None:
        if value is None:
            return None
        return msgspec.json.encode(value).decode("utf-8")

    @override
    def process_result_value(
            self, value: str | None, dialect: Dialect
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return msgspec.json.decode(value, type=dict[str, Any])


outbox_entries = Table(
    "outbox_entries",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("event_type", Enum(enums.OutboxEventType), nullable=False),
    Column("aggregate_id", String(255), nullable=False, index=True),
    Column("payload", PayloadType, nullable=False),
    Column("created_at", DateTime, nullable=False, index=True),
    Column("relayed_at", DateTime, nullable=True, index=True),
)


def start_mappers():
    """
    Initialize ORM mappings for all database models.
    """
    if mapper_registry.mappers:
        return

    _ = mapper_registry.map_imperatively(
        model.Document,
        documents,
        properties={
            # Custom column mapping for enum
            "file_type": documents.c.file_type,
        },
    )

    _ = mapper_registry.map_imperatively(
        model.Job,
        ocr_jobs,
        properties={
            "status": ocr_jobs.c.status,
            "document": relationship(
                model.Document, backref="jobs", foreign_keys=[ocr_jobs.c.document_id]
            ),
        },
    )

    _ = mapper_registry.map_imperatively(
        model.Result,
        ocr_results,
        properties={
            "job": relationship(
                model.Job, backref="result", foreign_keys=[ocr_results.c.job_id]
            ),
        },
    )

    _ = mapper_registry.map_imperatively(
        model.OutboxEntry,
        outbox_entries,
        properties={
            "event_type": outbox_entries.c.event_type,
        },
    )
