from typing import Any, override

import celery
from billiard.einfo import ExceptionInfo
from celery.utils.log import get_task_logger

from kul_ocr.entrypoints.celery_app import app
from kul_ocr.service_layer import services, uow

logger = get_task_logger(__name__)


class BaseTask(celery.Task):
    @override
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[str, Any],
        kwargs: dict[str, Any],
        einfo: ExceptionInfo,
    ):
        logger.error(
            "Task {} failed with error: {}".format(task_id, einfo),
        )


@app.task(bind=True, max_retries=3, base=BaseTask)
def process_ocr_job_task(self: BaseTask, job_id: str):
    """Process an OCR job asynchronously."""
    try:
        uow_instance = uow.SqlAlchemyUnitOfWork()

        with uow_instance:
            # Get job
            job = uow_instance.jobs.get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            _ = services.start_ocr_job_processing(job_id, uow_instance)

            uow_instance.commit()

        logger.info(f"Successfully processed job {job_id}")
        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        logger.error(f"Error processing job {job_id}: {exc}")

        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
