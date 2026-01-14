# # import pytest
# # from unittest.mock import patch, MagicMock
# # from pathlib import Path
# # from uuid import UUID
# # from typing import Any, cast
# #
# # from sqlalchemy.orm import sessionmaker, Session
# #
# # from kul_ocr.entrypoints.tasks import process_ocr_job_task
# # from kul_ocr.domain.model import JobStatus, SimpleOCRValue
# # from kul_ocr.service_layer.uow import SqlAlchemyUnitOfWork
# # from tests.factories import generate_document, generate_ocr_job
# #
# #
# # # def test_process_ocr_job_task_success(
# # #     uow: SqlAlchemyUnitOfWork,
# # #     monkeypatch: pytest.MonkeyPatch,
# # #     test_session_factory: sessionmaker[Session],
# # #     tmp_path: Path,
# # # ):
# # #     """Test that the OCR job task successfully processes a document and updates the database."""
# # #     # 1. Setup mock session factory so fresh_uow() uses our test DB
# # #     monkeypatch.setattr(
# # #         "kul_ocr.entrypoints.dependencies.get_session_factory",
# # #         lambda: test_session_factory,
# # #     )
# # #
# # #     # Mock config to use a temp directory for storage
# # #     mock_config = MagicMock()
# # #     mock_config.storage_root = tmp_path
# # #     monkeypatch.setattr(
# # #         "kul_ocr.entrypoints.dependencies.get_config", lambda: mock_config
# # #     )
# # #
# # #     # 2. Setup test data
# # #     doc = generate_document(dir_path=tmp_path)
# # #     job = generate_ocr_job(document_id=doc.id, status=JobStatus.PENDING)
# # #     job_id = job.id
# # #
# # #     with uow:
# # #         uow.documents.add(doc)
# # #         uow.jobs.add(job)
# # #         uow.commit()
# # #
# # #     # 3. Mock Tesseract Engine
# # #     with (
# # #         patch("kul_ocr.entrypoints.tasks.TesseractOCREngine") as MockEngine,
# # #         patch("kul_ocr.entrypoints.tasks.FileSystemDocumentLoader"),
# # #     ):
# # #         mock_engine_instance = MockEngine.return_value
# # #         mock_engine_instance.process_document.return_value = SimpleOCRValue(
# # #             content="Extracted text content"
# # #         )
# # #
# # #         # 4. Run the task directly using __wrapped__ to bypass Celery decorator magic
# # #         mock_self = MagicMock()
# # #         mock_self.request.retries = 0
# # #         mock_self.max_retries = 3
# # #
# # #         # Use Any cast to satisfy type checker for Celery-wrapped function
# # #         result = cast(Any, process_ocr_job_task).__wrapped__.__func__(mock_self, job_id)
# # #
# # #         # 5. Assertions on the return value
# # #         assert result.status == JobStatus.COMPLETED
# # #         assert result.job_id == UUID(job_id)
# # #
# # #         # 6. Verify database state
# # #         with uow:
# # #             updated_job = uow.jobs.get(job_id)
# # #             assert updated_job is not None
# # #             assert updated_job.status == JobStatus.COMPLETED
# # #
# # #             # Verify results were persisted
# # #             job_result = uow.results.get_by_job_id(job_id)
# # #             assert job_result is not None
# # #             assert job_result.content.content == "Extracted text content"
# # #
#
# def test_process_ocr_job_task_failure_and_retry(
#     uow: SqlAlchemyUnitOfWork,
#     monkeypatch: pytest.MonkeyPatch,
#     test_session_factory: sessionmaker[Session],
#     tmp_path: Path,
# ):
#     """Test that the task handles failures and triggers a retry."""
#     monkeypatch.setattr(
#         "kul_ocr.entrypoints.dependencies.get_session_factory",
#         lambda: test_session_factory,
#     )
#
#     mock_config = MagicMock()
#     mock_config.storage_root = tmp_path
#     monkeypatch.setattr(
#         "kul_ocr.entrypoints.dependencies.get_config", lambda: mock_config
#     )
#
#     doc = generate_document(dir_path=tmp_path)
#     job = generate_ocr_job(document_id=doc.id, status=JobStatus.PENDING)
#     job_id = job.id
#
#     with uow:
#         uow.documents.add(doc)
#         uow.jobs.add(job)
#         uow.commit()
#
#     with (
#         patch("kul_ocr.entrypoints.tasks.TesseractOCREngine") as MockEngine,
#         patch("kul_ocr.entrypoints.tasks.FileSystemDocumentLoader"),
#     ):
#         mock_engine_instance = MockEngine.return_value
#         mock_engine_instance.process_document.side_effect = Exception("OCR Failed")
#
#         mock_self = MagicMock()
#         mock_self.request.retries = 0
#         mock_self.max_retries = 3
#         mock_self.retry.side_effect = Exception("Retry raised")
#
#         with pytest.raises(Exception, match="Retry raised"):
#             cast(Any, process_ocr_job_task).__wrapped__.__func__(mock_self, job_id)
#
#         with uow:
#             updated_job = uow.jobs.get(job_id)
#             assert updated_job is not None
#             assert updated_job.status == JobStatus.PROCESSING
#
#
# def test_process_ocr_job_task_marks_failed_after_max_retries(
#     uow: SqlAlchemyUnitOfWork,
#     monkeypatch: pytest.MonkeyPatch,
#     test_session_factory: sessionmaker[Session],
#     tmp_path: Path,
# ):
#     """Test that the task marks the job as failed after exhausting all retries."""
#     monkeypatch.setattr(
#         "kul_ocr.entrypoints.dependencies.get_session_factory",
#         lambda: test_session_factory,
#     )
#
#     mock_config = MagicMock()
#     mock_config.storage_root = tmp_path
#     monkeypatch.setattr(
#         "kul_ocr.entrypoints.dependencies.get_config", lambda: mock_config
#     )
#
#     doc = generate_document(dir_path=tmp_path)
#     job = generate_ocr_job(document_id=doc.id, status=JobStatus.PENDING)
#     job_id = job.id
#
#     with uow:
#         uow.documents.add(doc)
#         uow.jobs.add(job)
#         uow.commit()
#
#     with (
#         patch("kul_ocr.entrypoints.tasks.TesseractOCREngine") as MockEngine,
#         patch("kul_ocr.entrypoints.tasks.FileSystemDocumentLoader"),
#     ):
#         mock_engine_instance = MockEngine.return_value
#         mock_engine_instance.process_document.side_effect = Exception(
#             "Permanent OCR Failure"
#         )
#
#         mock_self = MagicMock()
#         mock_self.request.retries = 3
#         mock_self.max_retries = 3
#         mock_self.retry.side_effect = Exception("Retry raised")
#
#         with pytest.raises(Exception, match="Retry raised"):
#             cast(Any, process_ocr_job_task).__wrapped__.__func__(mock_self, job_id)
#
#         with uow:
#             updated_job = uow.jobs.get(job_id)
#             assert updated_job is not None
#             assert updated_job.status == JobStatus.FAILED
