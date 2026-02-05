from collections.abc import Sequence
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ValidationInfo

from core.domain import enums, model, dto
from core.domain.enums import JobStatus
from core.utils.misc import nobeartype


class TextPartResponse(BaseModel):
    text: str
    confidence: float | None = None
    level: str

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class PagePartResponse(BaseModel):
    page_number: int
    width: int
    height: int
    parts: list[TextPartResponse]

    @field_validator("page_number")
    @classmethod
    def validate_page_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page number must be at least 1")
        return v

    @field_validator("width", "height")
    @classmethod
    @nobeartype
    def validate_dimensions(cls, v: int, info: ValidationInfo) -> int:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive (got {v})")
        return v


class ResultContentResponse(BaseModel):
    pages: list[PagePartResponse]

    @field_validator("pages")
    @classmethod
    def validate_pages_not_empty(
        cls, v: list[PagePartResponse]
    ) -> list[PagePartResponse]:
        if not v:
            raise ValueError("Result must contain at least one page")
        return v

    @classmethod
    def from_result_content(cls, content: Sequence[model.ProcessedPage]) -> Self:
        """Convert ProcessedPage sequence to ResultContentResponse.

        Used by both from_domain() and from_dto() to avoid duplication.
        """
        pages = []
        for processed_page in content:
            parts = [
                TextPartResponse(
                    text=part.text,
                    confidence=part.confidence,
                    level=part.level,
                )
                for part in processed_page.result.parts
            ]
            page_response = PagePartResponse(
                page_number=processed_page.result.metadata.page_number,
                width=processed_page.result.metadata.width,
                height=processed_page.result.metadata.height,
                parts=parts,
            )
            pages.append(page_response)
        return cls(pages=pages)

    @classmethod
    def from_domain(cls, result: model.Result) -> Self:
        return cls.from_result_content(result.content)


class TaskResponse(BaseModel):
    id: UUID = Field(..., description="UUID of the task")


class ProcessJobTaskResponse(TaskResponse):
    job_id: UUID
    task_id: UUID
    status: JobStatus


class OutboxEntryResponse(BaseModel):
    id: UUID
    event_type: enums.OutboxEventType
    aggregate_id: UUID
    created_at: datetime
    is_pending: bool
    relayed_at: datetime | None

    @classmethod
    def from_dto(cls, entry: dto.OutboxEntryDTO) -> Self:
        return cls(
            id=UUID(entry.id),
            aggregate_id=UUID(entry.aggregate_id),
            event_type=enums.OutboxEventType(entry.event_type),
            created_at=entry.created_at,
            is_pending=entry.is_pending,
            relayed_at=entry.relayed_at,
        )


class OutboxRelayerResponse(BaseModel):
    relayed_entries: list[OutboxEntryResponse]
    total: int

    @classmethod
    def from_dto(cls, entries: Sequence[dto.OutboxEntryDTO]) -> Self:
        return cls(
            relayed_entries=[OutboxEntryResponse.from_dto(entry) for entry in entries],
            total=len(entries),
        )
