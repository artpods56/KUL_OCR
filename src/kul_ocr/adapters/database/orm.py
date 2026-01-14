from datetime import datetime
from typing import Any, cast, final, override

import msgspec
from msgspec import Struct, field, Meta
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
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import registry as sqla_registry

from kul_ocr.domain import model

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
class OCRValueType(TypeDecorator[model.Result]):
    impl = Text
    cache_ok = True

    encoder = msgspec.json.Encoder()

    @override
    def process_bind_param(
        self, value: model.Result | None, dialect: Dialect
    ) -> str | None:
        """
        Encode a Result object into JSON string for storage.
        """
        if value is None:
            return None

        # Convert Result to a dict for JSON serialization
        data = {
            "id": value.id,
            "job_id": value.job_id,
            "creation_time": value.creation_time.isoformat(),
            "content": [
                {
                    "ref": {
                        "document_id": page.ref.document_id,
                        "index": page.ref.index,
                    },
                    "result": {
                        "parts": [
                            {
                                "text": part.text,
                                "bbox": {
                                    "x_min": part.bbox.x_min,
                                    "y_min": part.bbox.y_min,
                                    "x_max": part.bbox.x_max,
                                    "y_max": part.bbox.y_max,
                                },
                                "confidence": part.confidence,
                                "level": part.level,
                            }
                            for part in page.result.parts
                        ],
                        "metadata": {
                            "page_number": page.result.metadata.page_number,
                            "width": page.result.metadata.width,
                            "height": page.result.metadata.height,
                            "rotation": page.result.metadata.rotation,
                        },
                    }
                    for page in value.content
                }
            ],
        }
        
        return self.encoder.encode(data).decode("utf-8")

    @override
    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> model.Result | None:
        """
        Decode a JSON string from the database to a Result object.
        """
        if value is None:
            return None

        data = msgspec.json.decode(value)
        if not isinstance(data, dict):
            return None

        content = []
        for page_data in data.get("content", []):
            ref = model.PageRef(
                document_id=page_data["ref"]["document_id"],
                index=page_data["ref"]["index"],
            )

            parts = []
            for part_data in page_data["result"]["parts"]:
                bbox = model.BoundingBox(
                    x_min=part_data["bbox"]["x_min"],
                    y_min=part_data["bbox"]["y_min"],
                    x_max=part_data["bbox"]["x_max"],
                    y_max=part_data["bbox"]["y_max"],
                )
                text_part = model.TextPart(
                    text=part_data["text"],
                    bbox=bbox,
                    confidence=part_data.get("confidence"),
                    level=part_data["level"],
                )
                parts.append(text_part)

            metadata = model.PageMetadata(
                page_number=page_data["result"]["metadata"]["page_number"],
                width=page_data["result"]["metadata"]["width"],
                height=page_data["result"]["metadata"]["height"],
                rotation=page_data["result"]["metadata"].get("rotation", 0),
            )

            page_part = model.PagePart(parts=parts, metadata=metadata)
            processed_page = model.ProcessedPage(ref=ref, result=page_part)
            content.append(processed_page)

        return model.Result(
            id=data["id"],
            job_id=data["job_id"],
            creation_time=datetime.fromisoformat(data["creation_time"]),
            content=content,
        )

ocr_results = Table(
    "ocr_results",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("job_id", String(255), ForeignKey("ocr_jobs.id")),
    Column("content", OCRValueType),
)


def start_mappers():
    """
    Initialize ORM mappings for all database models.
    """
    if sqla_registry.mappers:
        return

    _ = sqla_registry.map_imperatively(
        model.Document,
        documents,
        properties={
            # Custom column mapping for enum
            "file_type": documents.c.file_type,
        },
    )

    _ = sqla_registry.map_imperatively(
        model.Job,
        ocr_jobs,
        properties={
            "status": ocr_jobs.c.status,
            "document": relationship(
                model.Document, backref="jobs", foreign_keys=[ocr_jobs.c.document_id]
            ),
        },
    )

    _ = sqla_registry.map_imperatively(
        model.Result,
        ocr_results,
        properties={
            "job": relationship(
                model.Job, backref="result", foreign_keys=[ocr_results.c.job_id]
            ),
        },
    )
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import registry as sqla_registry

from kul_ocr.domain import model

mapper_registry = sqla_registry.Registry()

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
class OCRValueType(TypeDecorator[model.Result]):
    impl = Text
    cache_ok = True

    encoder = msgspec.json.Encoder()

    @override
    def process_bind_param(
        self, value: model.Result | None, dialect: Dialect
    ) -> str | None:
        """
        Encode a Result object into JSON string for storage.
        """
        if value is None:
            return None

        # Convert Result to a dict for JSON serialization
        data = {
            "id": value.id,
            "job_id": value.job_id,
            "creation_time": value.creation_time.isoformat(),
            "content": [
                {
                    "ref": {
                        "document_id": page.ref.document_id,
                        "index": page.ref.index,
                    },
                    "result": {
                        "parts": [
                            {
                                "text": part.text,
                                "bbox": {
                                    "x_min": part.bbox.x_min,
                                    "y_min": part.bbox.y_min,
                                    "x_max": part.bbox.x_max,
                                    "y_max": part.bbox.y_max,
                                },
                                "confidence": part.confidence,
                                "level": part.level,
                            }
                            for part in page.result.parts
                        ],
                        "metadata": {
                            "page_number": page.result.metadata.page_number,
                            "width": page.result.metadata.width,
                            "height": page.result.metadata.height,
                            "rotation": page.result.metadata.rotation,
                        },
                    },
                }
                for page in value.content
            ],
        }

        return self.encoder.encode(data).decode("utf-8")

    @override
    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> model.Result | None:
        """
        Decode a JSON string from the database to a Result object.
        """
        if value is None:
            return None

        data = msgspec.json.decode(value)
        if not isinstance(data, dict):
            return None

        content = []
        for page_data in data.get("content", []):
            ref = model.PageRef(
                document_id=page_data["ref"]["document_id"],
                index=page_data["ref"]["index"],
            )

            parts = []
            for part_data in page_data["result"]["parts"]:
                bbox = model.BoundingBox(
                    x_min=part_data["bbox"]["x_min"],
                    y_min=part_data["bbox"]["y_min"],
                    x_max=part_data["bbox"]["x_max"],
                    y_max=part_data["bbox"]["y_max"],
                )
                text_part = model.TextPart(
                    text=part_data["text"],
                    bbox=bbox,
                    confidence=part_data.get("confidence"),
                    level=part_data["level"],
                )
                parts.append(text_part)

            metadata = model.PageMetadata(
                page_number=page_data["result"]["metadata"]["page_number"],
                width=page_data["result"]["metadata"]["width"],
                height=page_data["result"]["metadata"]["height"],
                rotation=page_data["result"]["metadata"].get("rotation", 0),
            )

            page_part = model.PagePart(parts=parts, metadata=metadata)
            processed_page = model.ProcessedPage(ref=ref, result=page_part)
            content.append(processed_page)

        return model.Result(
            id=data["id"],
            job_id=data["job_id"],
            creation_time=datetime.fromisoformat(data["creation_time"]),
            content=content,
        )


ocr_results = Table(
    "ocr_results",
    metadata,
    Column("id", String(255), primary_key=True),
    Column("job_id", String(255), ForeignKey("ocr_jobs.id")),
    Column("content", OCRValueType),
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
