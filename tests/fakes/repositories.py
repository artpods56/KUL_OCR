from collections.abc import Sequence
from datetime import datetime
from typing import final, override

import kul_ocr.adapters.database.repository
from kul_ocr.adapters.database.repository import (
    AbstractDocumentRepository,
    AbstractOCRJobRepository,
    AbstractOCRResultRepository,
    AbstractOutboxRepository,
)
from kul_ocr.domain import model, enums


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
    def get_or_raise(self, document_id: str) -> model.Document:
        document = self.get(document_id)
        if document is None:
            raise kul_ocr.adapters.database.repository.DocumentNotFoundError(
                document_id=document_id
            )
        return document

    @override
    def list_all(self) -> Sequence[model.Document]:
        return list(self._documents.values())


@final
class FakeOcrJobRepository(AbstractOCRJobRepository):
    def __init__(
        self,
        jobs: list[model.Job] | None = None,
        results_repo: "FakeOcrResultRepository | None" = None,
    ):
        self._jobs = {j.id: j for j in (jobs or [])}
        self._results_repo = results_repo
        self.added: list[model.Job] = []

    @override
    def add(self, ocr_job: model.Job) -> None:
        self._jobs[ocr_job.id] = ocr_job
        self.added.append(ocr_job)

    @override
    def get(self, ocr_job_id: str) -> model.Job | None:
        return self._jobs.get(ocr_job_id)

    @override
    def get_or_raise(self, job_id: str) -> model.Job:
        job = self.get(job_id)
        if job is None:
            raise kul_ocr.adapters.database.repository.OCRJobNotFoundError(
                job_id=job_id
            )
        return job

    @override
    def list_all(self) -> Sequence[model.Job]:
        return list(self._jobs.values())

    @override
    def list_by_status(self, job_status: enums.JobStatus) -> Sequence[model.Job]:
        return [j for j in self._jobs.values() if j.status == job_status]

    @override
    def list_by_document_id(self, document_id: str) -> Sequence[model.Job]:
        return [j for j in self._jobs.values() if j.document_id == document_id]

    @override
    def list_by_filters(
        self,
        status: enums.JobStatus | None = None,
        document_id: str | None = None,
    ) -> Sequence[model.Job]:
        jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        if document_id is not None:
            jobs = [j for j in jobs if j.document_id == document_id]
        return jobs

    @override
    def has_active_job_for_document(self, document_id: str) -> bool:
        return any(
            j.is_active and j.document_id == document_id for j in self._jobs.values()
        )

    @override
    def list_terminal_jobs(self) -> Sequence[model.Job]:
        return [j for j in self._jobs.values() if j.is_terminal]

    @override
    def get_latest_completed_for_document(self, document_id: str) -> model.Job | None:
        completed = [
            j
            for j in self._jobs.values()
            if j.document_id == document_id and j.status == enums.JobStatus.COMPLETED
        ]
        if not completed:
            return None
        return max(completed, key=lambda j: j.completed_at or j.created_at)

    @override
    def delete(self, ocr_job: model.Job) -> None:
        self._jobs.pop(ocr_job.id, None)

    @override
    def delete_with_cascade(self, job: model.Job) -> None:
        # Delete associated results if we have access to the results repository
        if self._results_repo:
            results_to_delete = [
                r for r in self._results_repo._results.values() if r.job_id == job.id
            ]
            for result in results_to_delete:
                self._results_repo.delete(result)
        # Then delete the job
        self._jobs.pop(job.id, None)


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

    @override
    def delete(self, ocr_result: model.Result) -> None:
        self._results.pop(ocr_result.id, None)


@final
class FakeOutboxRepository(AbstractOutboxRepository):
    def __init__(self, entries: list[model.OutboxEntry] | None = None):
        self._entries = {e.id: e for e in (entries or [])}
        self.added: list[model.OutboxEntry] = []

    @override
    def add(self, entry: model.OutboxEntry) -> None:
        self._entries[entry.id] = entry
        self.added.append(entry)

    @override
    def get(self, entry_id: str) -> model.OutboxEntry | None:
        return self._entries.get(entry_id)

    @override
    def get_or_raise(self, entry_id: str) -> model.OutboxEntry:
        entry = self.get(entry_id)
        if entry is None:
            raise kul_ocr.adapters.database.repository.OutboxEntryNotFoundError(
                entry_id=entry_id
            )
        return entry

    @override
    def list_pending(self, limit: int = 100) -> Sequence[model.OutboxEntry]:
        pending = [e for e in self._entries.values() if not e.is_relayed]
        # Sort by created_at ascending
        pending.sort(key=lambda e: e.created_at)
        return pending[:limit]

    @override
    def mark_as_relayed(self, entry_id: str) -> None:
        entry = self.get_or_raise(entry_id)
        entry.mark_as_relayed()

    @override
    def delete_relayed_older_than(self, cutoff: datetime) -> int:
        to_delete = [
            e
            for e in self._entries.values()
            if e.is_relayed and e.relayed_at is not None and e.relayed_at < cutoff
        ]
        for entry in to_delete:
            self._entries.pop(entry.id, None)
        return len(to_delete)
