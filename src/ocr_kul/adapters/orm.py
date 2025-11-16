from typing import Any, final, override, cast

import msgspec
from sqlalchemy import (
    Column,
    Date,
    Dialect,
    Engine,
    Integer,
    MetaData,
    Table,
    String,
    Text,
    Enum,
)
from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm import registry, relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.types import TypeDecorator

from ocr_kul.domain import model
from ocr_kul.domain.model import BaseOCRValue
from ocr_kul.service_layer.config import get_sqlite3_uri

mapper_registry = registry()

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("file_path", String(255), nullable=False),
    Column("file_type", Enum(model.FileType), nullable=False),
    Column("uploaded_at", Date, nullable=True),
    Column("file_size_bytes", Integer, nullable=True),
)

ocr_jobs = Table(
    "ocr_jobs",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("document_id", String(255), ForeignKey("documents.id")),
    Column("created_at", Date),
    Column("error_message", String(255), nullable=True),
    Column("started_at", Date, nullable=True),
    Column("completed_at", Date, nullable=True),
    Column("status", Enum(model.JobStatus), nullable=False),
)


@final
class OCRValueType(TypeDecorator[model.OCRValueTypes]):
    impl = Text
    cache_ok = True

    decoder = msgspec.json.Decoder(type=model.OCRValueTypes)
    encoder = msgspec.json.Encoder()

    @override
    def process_bind_param(
        self, value: BaseOCRValue[Any] | None, dialect: Dialect
    ) -> str | None:
        """
        Encode object as a JSON string.
        """
        if value is None:
            return None
        return self.encoder.encode(value).decode("utf-8")

    @override
    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> model.OCRValueTypes | None:
        """
        Decode object from a JSON string.
        """
        if value is None:
            return None

        return cast(model.OCRValueTypes, self.decoder.decode(value))


ocr_results = Table(
    "ocr_results",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("job_id", String(255), ForeignKey("ocr_jobs.id")),
    Column("content", OCRValueType),
)


def start_mappers():
    _ = mapper_registry.map_imperatively(
        model.Document,
        documents,
        properties={
            # Custom column mapping for enum
            "file_type": documents.c.file_type,
        },
    )

    _ = mapper_registry.map_imperatively(
        model.OCRJob,
        ocr_jobs,
        properties={
            "status": ocr_jobs.c.status,
            "document": relationship(
                model.Document, backref="jobs", foreign_keys=[ocr_jobs.c.document_id]
            ),
        },
    )

    _ = mapper_registry.map_imperatively(
        model.OCRResult,
        ocr_results,
        properties={
            "job": relationship(
                model.OCRJob, backref="result", foreign_keys=[ocr_results.c.job_id]
            ),
        },
    )


def create_database(db_uri: str | None = None) -> Engine:
    engine = create_engine(
        db_uri if db_uri is not None else get_sqlite3_uri(), echo=True, future=True
    )

    # Create all tables
    metadata.create_all(engine)

    return engine


def get_session(engine: Engine) -> Session:
    return Session(engine)


def get_engine(db_uri: str | None = None) -> Engine:
    db_uri = db_uri or get_sqlite3_uri()
    return create_engine(db_uri)
