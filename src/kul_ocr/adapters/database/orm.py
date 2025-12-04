from typing import Any, cast, final, override

import msgspec
from sqlalchemy import (
    Column,
    Date,
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

from kul_ocr.domain import model
from kul_ocr.domain.model import BaseOCRValue

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
        Encode a Python OCR value object into JSON string for storage.
        
        Args:
            value: OCR value object to encode.
            dialect: The database dialect in use (provided by SQLAlchemy).
            
        Returns:
            A JSON encoded string reprezenting the OCR value, or 'None'
            if input value is 'None'
        """
        if value is None:
            return None
        return self.encoder.encode(value).decode("utf-8")

    @override
    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> model.OCRValueTypes | None:
        """
        Decode a JSON string from the database to Python OCR value object.
        
        Args:
            value: The JSON string retrieved from the database.
            dialect: The database dialect in use (provided by SQLAlchemy).
            
        Returns:
            A Python ORC value object , or 'None'
            if input value is 'None'
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
    """
        Inirialize ORM mappings for all database models.
        
        Registers the relationshipb between Python classes and database tables
        with the SQLAlchemy apper registry. Must be called before pergorming and databese
        operations that rely on these mappings.
        
        Args:
            None
            
        Returns:
            None
        """
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
