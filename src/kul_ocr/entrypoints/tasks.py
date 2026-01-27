from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, override, Unpack, TypedDict

import celery
from billiard.einfo import ExceptionInfo
from celery.utils.log import get_task_logger

import kul_ocr.service_layer.services.documents

from kul_ocr.domain import enums
from kul_ocr.entrypoints.celery_app import app
from kul_ocr.entrypoints import dependencies
from kul_ocr.entrypoints.dependencies import fresh_uow, get_task_runner
from kul_ocr.service_layer.helpers import generate_id
from kul_ocr.service_layer.services import outbox, jobs

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
        relayed_entries = outbox.relay_pending_outbox_entries(
            task_runner=task_runner,
            uow=fresh_uow(),
            batch_size=100,
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
            deleted_count = outbox.cleanup_old_outbox_entries(
                uow=uow,
                retention_hours=24,
            )

        return {"deleted_count": deleted_count}

    except Exception as exc:
        logger.error(f"Failed to clean up outbox entries: {exc}")
        raise self.retry(exc=exc, countdown=60)  # pyright: ignore[reportAny]


@app.task(bind=True, max_retries=3)
def process_ocr_job_task(self, job_id: str):
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


class UploadDocumentTaskKwargs(TypedDict):
    document_id: str
    staging_file_path: str
    uploaded_file_path: str


@app.task(bind=True, max_retries=3)
def upload_document(self, **kwargs: Unpack[UploadDocumentTaskKwargs]):
    document_id = kwargs["document_id"]
    staging_file_path = kwargs["staging_file_path"]
    uploaded_file_path = kwargs["uploaded_file_path"]

    with fresh_uow() as uow:
        document = uow.documents.get_or_raise(document_id)

        if document.status == enums.DocumentStatus.READY:
            return

        try:
            storage = dependencies.get_file_storage()

            storage.move(
                source_path=Path(staging_file_path),
                destination_path=Path(uploaded_file_path),
            )

            document.update_status(enums.DocumentStatus.READY)
            uow.commit()

        except Exception as e:
            logger.error(
                "Failed to upload document.",
                document_id=document_id,
                error=str(e),
            )
            if self.request.retries >= self.max_retries:
                with fresh_uow() as uow:
                    document = uow.documents.get_or_raise(document_id)
                    document.update_status(enums.DocumentStatus.FAILED)
                    uow.commit()

            raise
