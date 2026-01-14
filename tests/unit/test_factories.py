from collections.abc import Sequence
from pathlib import Path


from kul_ocr.domain import model
from tests import factories


class TestGenerateOCRJob:
    """Tests for generate_ocr_job factory."""

    def test_generates_job_with_pending_status_by_default(self):
        job = factories.generate_ocr_job()

        assert isinstance(job, model.Job)
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
        assert all(isinstance(job, model.Job) for job in jobs)

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


class TestGenerateTextPart:
    """Tests for generate_text_part factory."""

    def test_generates_text_part(self):
        text_part = factories.generate_text_part()

        assert isinstance(text_part, model.TextPart)
        assert isinstance(text_part.text, str)
        assert isinstance(text_part.bbox, model.BoundingBox)
        assert isinstance(text_part.level, str)
        assert text_part.level in ["word", "line", "block"]

    def test_generates_unique_text_parts(self):
        text_part1 = factories.generate_text_part()
        text_part2 = factories.generate_text_part()

        assert text_part1.text != text_part2.text


class TestGeneratePagePart:
    """Tests for generate_page_part factory."""

    def test_generates_page_part(self):
        page_part = factories.generate_page_part()

        assert isinstance(page_part, model.PagePart)
        assert isinstance(page_part.parts, Sequence)
        assert len(page_part.parts) >= 1
        assert isinstance(page_part.metadata, model.PageMetadata)

    def test_generates_page_part_with_custom_dimensions(self):
        page_part = factories.generate_page_part(width=800, height=1000)

        assert page_part.metadata.width == 800
        assert page_part.metadata.height == 1000


class TestGenerateProcessedPage:
    """Tests for generate_processed_page factory."""

    def test_generates_processed_page(self):
        processed_page = factories.generate_processed_page()

        assert isinstance(processed_page, model.ProcessedPage)
        assert isinstance(processed_page.ref, model.PageRef)
        assert isinstance(processed_page.result, model.PagePart)


class TestGenerateOCRResult:
    """Tests for generate_ocr_result factory."""

    def test_generates_result(self):
        result = factories.generate_ocr_result()

        assert isinstance(result, model.Result)
        assert isinstance(result.id, str)
        assert isinstance(result.job_id, str)
        assert isinstance(result.content, Sequence)
        assert len(result.content) >= 1

    def test_generates_result_with_single_page(self):
        result = factories.generate_ocr_result(pages_count=1)

        assert len(result.content) == 1
        assert result.content[0].ref.index == 0

    def test_generates_result_with_multiple_pages(self):
        result = factories.generate_ocr_result(pages_count=5)

        assert len(result.content) == 5
        for i, page in enumerate(result.content):
            assert page.ref.index == i

    def test_generates_result_with_specified_document_id(self):
        doc_id = "custom-doc-id-123"
        result = factories.generate_ocr_result(document_id=doc_id)

        assert result.content[0].ref.document_id == doc_id
        assert all(page.ref.document_id == doc_id for page in result.content)

    def test_generates_results_with_unique_ids(self):
        result1 = factories.generate_ocr_result()
        result2 = factories.generate_ocr_result()

        assert result1.id != result2.id


class TestGenerateOCRResults:
    """Tests for generate_ocr_results factory."""

    def test_generates_default_count_of_results(self):
        results = factories.generate_ocr_results()

        assert len(results) == 10
        assert all(isinstance(result, model.Result) for result in results)

    def test_generates_specified_count_of_results(self):
        results = factories.generate_ocr_results(results_count=5)

        assert len(results) == 5

    def test_generates_results_with_unique_ids(self):
        results = factories.generate_ocr_results(results_count=20)
        result_ids = [r.id for r in results]

        assert len(result_ids) == len(set(result_ids))

    def test_generates_empty_list_when_count_is_zero(self):
        results = factories.generate_ocr_results(results_count=0)

        assert len(results) == 0

    def test_all_results_have_different_job_ids(self):
        results = factories.generate_ocr_results(results_count=5)
        job_ids = [r.job_id for r in results]

        # Each result should have its own job_id
        assert len(job_ids) == len(set(job_ids))
