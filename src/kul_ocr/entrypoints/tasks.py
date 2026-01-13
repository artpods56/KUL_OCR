from collections.abc import Mapping, Sequence
from typing import Any, override
from uuid import UUID

import celery
from billiard.einfo import ExceptionInfo
from celery.utils.log import get_task_logger

from kul_ocr.domain.model import JobStatus
from kul_ocr.entrypoints.celery_app import app
from kul_ocr.entrypoints import dependencies
from kul_ocr.entrypoints.dependencies import fresh_uow
from kul_ocr.entrypoints.schemas import ProcessOCRJobTaskResponse
from kul_ocr.service_layer import services
from kul_ocr.service_layer.helpers import generate_id

logger = get_task_logger(__name__)


class BaseTask(celery.Task):  # pyright: ignore[reportMissingTypeArgument]
    @override
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: Sequence[Any],
        kwargs: Mapping[str, Any],
        einfo: ExceptionInfo,
    ):
        """Generic failure handler."""
        logger.error(f"Task {task_id} failed: {einfo}")


@app.task(bind=True, max_retries=3, base=BaseTask)
def process_ocr_job_task(self: BaseTask, job_id: str) -> ProcessOCRJobTaskResponse:
    """Process an OCR job asynchronously using split transactions."""
    ocr_engine = dependencies.get_ocr_engine()
    document_loader = dependencies.get_document_loader()

    try:
        # Idempotent start: check if job is already processing
        with fresh_uow() as uow:
            job = services.get_ocr_job(job_id, uow)
            if job.status == JobStatus.PENDING:
                job = services.start_ocr_job_processing(UUID(job_id), uow)
            document_id = job.document_id
            uow.commit()

        with fresh_uow() as uow:
            doc_input = services.get_document_for_processing(str(document_id), uow)

        logger.info(f"Starting OCR processing for job {job_id}")
        result = services.process_document(
            doc_input=doc_input,
            ocr_engine=ocr_engine,
            document_loader=document_loader,
        )

        with fresh_uow() as uow:
            _ = services.complete_ocr_job(job_id, result, uow)
            uow.commit()

        logger.info(f"Successfully processed job {job_id}")
        return ProcessOCRJobTaskResponse(
            id=UUID(generate_id()), status=JobStatus.COMPLETED, job_id=UUID(job_id)
        )

    except Exception as exc:
        logger.error(f"Error processing job {job_id}: {exc}")

        # Only mark as failed if we are giving up (all retries exhausted)
        if self.max_retries is not None and self.request.retries >= self.max_retries:
            try:
                with fresh_uow() as uow:
                    _ = services.fail_ocr_job(UUID(job_id), str(exc), uow)
                    uow.commit()
                logger.info(f"Marked job {job_id} as failed after exhausting retries")
            except Exception as fail_exc:
                logger.error(f"Failed to mark job {job_id} as failed: {fail_exc}")

        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))  # pyright: ignore[reportAny]
