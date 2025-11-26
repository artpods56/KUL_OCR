from dataclasses import dataclass, field
from typing import override, Sequence, Any

from kul_ocr.adapters.database.repository import (
    AbstractDocumentRepository,
    AbstractOCRJobRepository,
    AbstractOCRResultRepository,
)
from kul_ocr.domain import model


@dataclass
class FakeDocumentsRepository:
    """Type-safe fake for the documents repository."""

    added: list[model.Document] = field(default_factory=list)

    def add(self, document: model.Document) -> None:
        self.added.append(document)


class FakeDocumentRepository(AbstractDocumentRepository):
    def __init__(self):
        self._documents: dict[str, model.Document] = {}
        self.added: list[model.Document] = []

    @override
    def add(self, document: model.Document):
        self._documents[document.id] = document
        self.added.append(document)

    @override
    def get(self, document_id: str):
        return self._documents.get(document_id, None)

    @override
    def list_all(self) -> Sequence[model.Document]:
        return list(self._documents.values())


class FakeOcrJobRepository(AbstractOCRJobRepository):
    def __init__(self):
        self._ocr_jobs: dict[str, model.OCRJob] = {}

    @override
    def add(self, ocr_job: model.OCRJob):
        self._ocr_jobs[ocr_job.id] = ocr_job

    @override
    def get(self, ocr_job_id: str) -> model.OCRJob | None:
        return self._ocr_jobs.get(ocr_job_id, None)

    @override
    def list_all(self) -> Sequence[model.OCRJob]:
        return list(self._ocr_jobs.values())

    @override
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.OCRJob]:
        return [job for job in self._ocr_jobs.values() if job.status == job_status]

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.OCRJob]:
        return [
            job for job in self._ocr_jobs.values() if job.document_id == document_id
        ]

    @override
    def list_terminal_jobs(self) -> Sequence[model.OCRJob]:
        return [job for job in self._ocr_jobs.values() if job.is_terminal]


class FakeOcrResultRepository(AbstractOCRResultRepository):
    def __init__(self):
        self._ocr_results: dict[str, model.OCRResult[Any]] = {}

    @override
    def add(self, ocr_result: model.OCRResult[Any]) -> None:
        self._ocr_results[ocr_result.id] = ocr_result

    @override
    def get(self, ocr_result_id: str) -> model.OCRResult[Any] | None:
        return self._ocr_results.get(ocr_result_id, None)

    @override
    def list_all(self) -> Sequence[model.OCRResult[Any]]:
        return list(self._ocr_results.values())
