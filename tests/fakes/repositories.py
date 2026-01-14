from collections.abc import Sequence
from typing import final, override

from kul_ocr.adapters.database.repository import (
    AbstractDocumentRepository,
    AbstractOCRJobRepository,
    AbstractOCRResultRepository,
)
from kul_ocr.domain import model


@final
class FakeDocumentRepository(AbstractDocumentRepository):
    def __init__(self, documents: list[model.Document] | None = None):
        self._documents = {d.id: d for d in (documents or [])}
        self.added: list[model.Document] = []

    @override
    def add(self, document: model.Document) -> None:
        self._documents[document.id] = document
        self.added.append(document)

    @override
    def get(self, document_id: str) -> model.Document | None:
        return self._documents.get(document_id)

    @override
    def list_all(self) -> Sequence[model.Document]:
        return list(self._documents.values())


@final
class FakeOcrJobRepository(AbstractOCRJobRepository):
    def __init__(self, jobs: list[model.Job] | None = None):
        self._jobs = {j.id: j for j in (jobs or [])}
        self.added: list[model.Job] = []

    @override
    def add(self, ocr_job: model.Job) -> None:
        self._jobs[ocr_job.id] = ocr_job
        self.added.append(ocr_job)

    @override
    def get(self, ocr_job_id: str) -> model.Job | None:
        return self._jobs.get(ocr_job_id)

    @override
    def list_all(self) -> Sequence[model.Job]:
        return list(self._jobs.values())

    @override
    def list_by_status(self, job_status: model.JobStatus) -> Sequence[model.Job]:
        return [j for j in self._jobs.values() if j.status == job_status]

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.Job]:
        return [j for j in self._jobs.values() if j.document_id == document_id]

    @override
    def list_terminal_jobs(self) -> Sequence[model.Job]:
        return [j for j in self._jobs.values() if j.is_terminal]

    @override
    def get_latest_completed_for_document(self, document_id: str) -> model.Job | None:
        completed = [
            j
            for j in self._jobs.values()
            if j.document_id == document_id and j.status == model.JobStatus.COMPLETED
        ]
        if not completed:
            return None
        return max(completed, key=lambda j: j.completed_at or j.created_at)


@final
class FakeOcrResultRepository(AbstractOCRResultRepository):
    def __init__(self, results: list[model.Result] | None = None):
        self._results = {r.id: r for r in (results or [])}
        self.added: list[model.Result] = []

    @override
    def add(self, ocr_result: model.Result) -> None:
        self._results[ocr_result.id] = ocr_result
        self.added.append(ocr_result)

    @override
    def get(self, ocr_result_id: str) -> model.Result | None:
        return self._results.get(ocr_result_id)

    @override
    def list_all(self) -> Sequence[model.Result]:
        return list(self._results.values())

    @override
    def get_by_job_id(self, job_id: str) -> model.Result | None:
        return next((r for r in self._results.values() if r.job_id == job_id), None)
