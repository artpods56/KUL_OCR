from collections.abc import Mapping, Sequence
from typing import Any, override

import celery
from billiard.einfo import ExceptionInfo
from celery.utils.log import get_task_logger

import kul_ocr.service_layer.services.documents
import kul_ocr.service_layer.services.jobs
import kul_ocr.service_layer.services.outbox
from kul_ocr.entrypoints.celery_app import app
from kul_ocr.entrypoints import dependencies
from kul_ocr.entrypoints.dependencies import fresh_uow, get_task_runner

logger = get_task_logger(__name__)


# --- Outbox Relay Tasks ---


@app.task(bind=True, max_retries=3)
def relay_outbox_task(self: celery.Task) -> dict[str, Any]:  # pyright: ignore[reportMissingTypeArgument]
    """Relay pending outbox entries to Celery.

    This task runs periodically (via Celery Beat) to pick up any pending
    outbox entries and schedule the corresponding Celery tasks.

    Returns:
        Dictionary with relay statistics.
    """
    task_runner = get_task_runner()

    try:
        relayed_entries = (
            kul_ocr.service_layer.services.outbox.relay_pending_outbox_entries(
                task_runner=task_runner,
                uow=fresh_uow(),
                batch_size=100,
            )
        )

        return {"relayed_count": len(relayed_entries)}

    except Exception as exc:
        logger.error(f"Failed to relay outbox entries: {exc}")
        raise self.retry(exc=exc, countdown=10)  # pyright: ignore[reportAny]


@app.task(bind=True, max_retries=3)
def cleanup_outbox_task(self: celery.Task) -> dict[str, int]:  # pyright: ignore[reportMissingTypeArgument]
    """Clean up old relayed outbox entries.

    This task runs periodically (via Celery Beat) to remove old relayed
    outbox entries and prevent unbounded table growth.

    Returns:
        Dictionary with cleanup statistics.
    """
    try:
        with fresh_uow() as uow:
            deleted_count = (
                kul_ocr.service_layer.services.outbox.cleanup_old_outbox_entries(
                    uow=uow,
                    retention_hours=24,
                )
            )

        return {"deleted_count": deleted_count}

    except Exception as exc:
        logger.error(f"Failed to clean up outbox entries: {exc}")
        raise self.retry(exc=exc, countdown=60)  # pyright: ignore[reportAny]


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
def process_ocr_job_task(self: BaseTask, job_id: str):
    """Process an OCR job asynchronously using split transactions.

    This task is scheduled by the outbox relay after start_ocr_job_processing
    has already marked the job as PROCESSING.
    """
    ocr_engine = dependencies.get_ocr_engine()
    document_loader = dependencies.get_document_loader()

    try:
        # Get job info - job should already be in PROCESSING state
        with fresh_uow() as uow:
            job_dto = kul_ocr.service_layer.services.jobs.get_ocr_job(job_id, uow)
            document_id = job_dto.document_id

        with fresh_uow() as uow:
            doc_input = (
                kul_ocr.service_layer.services.documents.get_document_for_processing(
                    str(document_id), uow
                )
            )

        logger.info(f"Starting OCR processing for job {job_id}")
        result_dto = kul_ocr.service_layer.services.documents.process_document(
            doc_input=doc_input,
            ocr_engine=ocr_engine,
            document_loader=document_loader,
        )

        with fresh_uow() as uow:
            _ = kul_ocr.service_layer.services.jobs.complete_ocr_job(
                job_id, result_dto, uow
            )
            uow.commit()

        logger.info(f"Successfully processed job {job_id}")

    except Exception as exc:
        logger.error(f"Error processing job {job_id}: {exc}")

        # Only mark as failed if we are giving up (all retries exhausted)
        if self.max_retries is not None and self.request.retries >= self.max_retries:
            try:
                with fresh_uow() as uow:
                    _ = kul_ocr.service_layer.services.jobs.fail_ocr_job(
                        job_id, str(exc), uow
                    )
                    uow.commit()
                logger.info(f"Marked job {job_id} as failed after exhausting retries")
            except Exception as fail_exc:
                logger.error(f"Failed to mark job {job_id} as failed: {fail_exc}")

        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))  # pyright: ignore[reportAny]
