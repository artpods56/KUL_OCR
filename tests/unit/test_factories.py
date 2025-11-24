from collections.abc import Sequence
from pathlib import Path

import pytest

from kul_ocr.domain import model
from tests import factories


class TestGenerateOCRJob:
    """Tests for generate_ocr_job factory."""

    def test_generates_job_with_pending_status_by_default(self):
        job = factories.generate_ocr_job()

        assert isinstance(job, model.OCRJob)
        assert job.status == model.JobStatus.PENDING
        assert isinstance(job.id, str)
        assert len(job.id) > 0
        assert isinstance(job.document_id, str)
        assert len(job.document_id) > 0

    def test_generates_job_with_specified_status(self):
        job = factories.generate_ocr_job(status=model.JobStatus.COMPLETED)

        assert job.status == model.JobStatus.COMPLETED

    def test_generates_job_with_processing_status(self):
        job = factories.generate_ocr_job(status=model.JobStatus.PROCESSING)

        assert job.status == model.JobStatus.PROCESSING

    def test_generates_job_with_failed_status(self):
        job = factories.generate_ocr_job(status=model.JobStatus.FAILED)

        assert job.status == model.JobStatus.FAILED

    def test_generates_unique_job_ids(self):
        job1 = factories.generate_ocr_job()
        job2 = factories.generate_ocr_job()

        assert job1.id != job2.id
        assert job1.document_id != job2.document_id

    def test_generates_job_with_random_status_when_none(self):
        job = factories.generate_ocr_job(status=None)

        assert job.status in list(model.JobStatus)


class TestGenerateOCRJobs:
    """Tests for generate_ocr_jobs factory."""

    def test_generates_default_count_of_jobs(self):
        jobs = factories.generate_ocr_jobs()

        assert len(jobs) == 10
        assert all(isinstance(job, model.OCRJob) for job in jobs)

    def test_generates_specified_count_of_jobs(self):
        jobs = factories.generate_ocr_jobs(jobs_count=5)

        assert len(jobs) == 5

    def test_generates_jobs_with_specified_status(self):
        jobs = factories.generate_ocr_jobs(
            jobs_count=3, status=model.JobStatus.COMPLETED
        )

        assert all(job.status == model.JobStatus.COMPLETED for job in jobs)

    def test_generates_jobs_with_unique_ids(self):
        jobs = factories.generate_ocr_jobs(jobs_count=20)
        job_ids = [job.id for job in jobs]

        assert len(job_ids) == len(set(job_ids))

    def test_generates_empty_list_when_count_is_zero(self):
        jobs = factories.generate_ocr_jobs(jobs_count=0)

        assert len(jobs) == 0


class TestGenerateDocument:
    """Tests for generate_document factory."""

    def test_generates_document_with_random_file_type(self, tmp_path: Path):
        document = factories.generate_document(dir_path=tmp_path)

        assert isinstance(document, model.Document)
        assert isinstance(document.id, str)
        assert len(document.id) > 0
        assert document.file_type in list(model.FileType)
        assert document.file_size_bytes == 0
        assert str(tmp_path) in document.file_path

    def test_generates_document_with_specified_file_type(self, tmp_path: Path):
        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PDF
        )

        assert document.file_type == model.FileType.PDF

    def test_generates_document_with_specified_file_size(self, tmp_path: Path):
        document = factories.generate_document(
            dir_path=tmp_path, file_size_in_bytes=1024
        )

        assert document.file_size_bytes == 1024

    def test_generates_document_with_unique_ids(self, tmp_path: Path):
        doc1 = factories.generate_document(dir_path=tmp_path)
        doc2 = factories.generate_document(dir_path=tmp_path)

        assert doc1.id != doc2.id
        assert doc1.file_path != doc2.file_path

    def test_generates_document_with_all_file_types(self, tmp_path: Path):
        for file_type in model.FileType:
            document = factories.generate_document(
                dir_path=tmp_path, file_type=file_type
            )

            assert document.file_type == file_type


class TestGenerateDocuments:
    """Tests for generate_documents factory."""

    def test_generates_default_count_of_documents(self, tmp_path: Path):
        documents = factories.generate_documents(dir_path=tmp_path)

        assert len(documents) == 10
        assert all(isinstance(doc, model.Document) for doc in documents)

    def test_generates_specified_count_of_documents(self, tmp_path: Path):
        documents = factories.generate_documents(dir_path=tmp_path, documents_count=5)

        assert len(documents) == 5

    def test_generates_documents_with_specified_file_type(self, tmp_path: Path):
        documents = factories.generate_documents(
            dir_path=tmp_path, documents_count=3, file_type=model.FileType.PNG
        )

        assert all(doc.file_type == model.FileType.PNG for doc in documents)

    def test_generates_documents_with_unique_ids(self, tmp_path: Path):
        documents = factories.generate_documents(dir_path=tmp_path, documents_count=15)
        doc_ids = [doc.id for doc in documents]

        assert len(doc_ids) == len(set(doc_ids))

    def test_generates_documents_with_unique_file_paths(self, tmp_path: Path):
        documents = factories.generate_documents(dir_path=tmp_path, documents_count=15)
        file_paths = [doc.file_path for doc in documents]

        assert len(file_paths) == len(set(file_paths))

    def test_generates_empty_list_when_count_is_zero(self, tmp_path: Path):
        documents = factories.generate_documents(dir_path=tmp_path, documents_count=0)

        assert len(documents) == 0


class TestOCRValueFactory:
    """Tests for ocr_value_factory function."""

    def test_generates_simple_ocr_value(self):
        value = factories.ocr_value_factory(value_type=model.SimpleOCRValue)

        assert isinstance(value, model.SimpleOCRValue)
        assert isinstance(value.content, str)
        assert len(value.content) > 0

    def test_generates_single_page_ocr_value(self):
        value = factories.ocr_value_factory(value_type=model.SinglePageOcrValue)

        assert isinstance(value, model.SinglePageOcrValue)
        assert isinstance(value.content, str)
        assert isinstance(value.page_number, int)
        assert 1 <= value.page_number <= 100

    def test_generates_multi_page_ocr_value(self):
        value = factories.ocr_value_factory(value_type=model.MultiPageOcrValue)

        assert isinstance(value, model.MultiPageOcrValue)
        assert isinstance(value.content, Sequence)
        assert len(value.content) >= 1
        assert all(isinstance(page, model.SinglePageOcrValue) for page in value.content)

    def test_raises_error_for_unknown_value_type(self):
        # Create a dummy type that's not in the factory map
        class UnknownOCRValue(model.BaseOCRValue[str]):
            content: str

        with pytest.raises(
            ValueError, match="Unknown value type for OCR Results factory"
        ):
            _ = factories.ocr_value_factory(value_type=UnknownOCRValue)

    def test_generates_unique_simple_values(self):
        value1 = factories.ocr_value_factory(value_type=model.SimpleOCRValue)
        value2 = factories.ocr_value_factory(value_type=model.SimpleOCRValue)

        # UUID-based content should be unique
        assert value1.content != value2.content

    def test_multi_page_value_has_valid_pages(self):
        value = factories.ocr_value_factory(value_type=model.MultiPageOcrValue)

        for page in value.content:
            assert isinstance(page.page_number, int)
            assert page.page_number >= 1
            assert isinstance(page.content, str)
            assert len(page.content) > 0


class TestGenerateOCRResult:
    """Tests for generate_ocr_result factory."""

    def test_generates_result_with_simple_value(self):
        result = factories.generate_ocr_result(value_type=model.SimpleOCRValue)

        assert isinstance(result, model.OCRResult)
        assert isinstance(result.id, str)
        assert isinstance(result.job_id, str)
        assert isinstance(result.content, model.SimpleOCRValue)

    def test_generates_result_with_single_page_value(self):
        result = factories.generate_ocr_result(value_type=model.SinglePageOcrValue)

        assert isinstance(result.content, model.SinglePageOcrValue)

    def test_generates_result_with_multi_page_value(self):
        result = factories.generate_ocr_result(value_type=model.MultiPageOcrValue)

        assert isinstance(result.content, model.MultiPageOcrValue)

    def test_generates_result_with_specified_job_id(self):
        job_id = "custom-job-id-123"
        result = factories.generate_ocr_result(
            value_type=model.SimpleOCRValue, job_id=job_id
        )

        assert result.job_id == job_id

    def test_generates_result_with_auto_job_id_when_none(self):
        result = factories.generate_ocr_result(value_type=model.SimpleOCRValue)

        assert isinstance(result.job_id, str)
        assert len(result.job_id) > 0

    def test_generates_results_with_unique_ids(self):
        result1 = factories.generate_ocr_result(value_type=model.SimpleOCRValue)
        result2 = factories.generate_ocr_result(value_type=model.SimpleOCRValue)

        assert result1.id != result2.id


class TestGenerateOCRResults:
    """Tests for generate_ocr_results factory."""

    def test_generates_default_count_of_results(self):
        results = factories.generate_ocr_results(value_type=model.SimpleOCRValue)

        assert len(results) == 10
        assert all(isinstance(result, model.OCRResult) for result in results)

    def test_generates_specified_count_of_results(self):
        results = factories.generate_ocr_results(
            value_type=model.SimpleOCRValue, results_count=5
        )

        assert len(results) == 5

    def test_generates_results_with_simple_value_type(self):
        results = factories.generate_ocr_results(
            value_type=model.SimpleOCRValue, results_count=3
        )

        assert all(isinstance(r.content, model.SimpleOCRValue) for r in results)

    def test_generates_results_with_single_page_value_type(self):
        results = factories.generate_ocr_results(
            value_type=model.SinglePageOcrValue, results_count=3
        )

        assert all(isinstance(r.content, model.SinglePageOcrValue) for r in results)

    def test_generates_results_with_multi_page_value_type(self):
        results = factories.generate_ocr_results(
            value_type=model.MultiPageOcrValue, results_count=3
        )

        assert all(isinstance(r.content, model.MultiPageOcrValue) for r in results)

    def test_generates_results_with_unique_ids(self):
        results = factories.generate_ocr_results(
            value_type=model.SimpleOCRValue, results_count=20
        )
        result_ids = [r.id for r in results]

        assert len(result_ids) == len(set(result_ids))

    def test_generates_empty_list_when_count_is_zero(self):
        results = factories.generate_ocr_results(
            value_type=model.SimpleOCRValue, results_count=0
        )

        assert len(results) == 0

    def test_all_results_have_different_job_ids(self):
        results = factories.generate_ocr_results(
            value_type=model.SimpleOCRValue, results_count=5
        )
        job_ids = [r.job_id for r in results]

        # Each result should have its own job_id
        assert len(job_ids) == len(set(job_ids))
