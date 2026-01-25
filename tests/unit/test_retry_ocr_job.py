import kul_ocr.adapters.database.repository
import kul_ocr.domain.model
import kul_ocr.service_layer.services.jobs
from kul_ocr.domain import model, structs, enums, exceptions
import pytest
from uuid import uuid4


def test_retry_failed_job_creates_new_pending_job(uow):
    failed_job = model.Job(id=str(uuid4()), document_id=str(uuid4()))
    failed_job.update_status(enums.JobStatus.FAILED, error_message="OCR error")
    uow.jobs.add(failed_job)
    uow.commit()

    response: structs.JobDTO = kul_ocr.service_layer.services.jobs.retry_ocr_job(
        failed_job.id, uow
    )
    assert str(response.id) != failed_job.id
    assert str(response.document_id) == failed_job.document_id
    assert response.status == "pending"

    original_job = uow.jobs.get(failed_job.id)
    assert original_job.status == enums.JobStatus.FAILED


def test_retry_non_failed_job_raises_error(uow):
    job = model.Job(id=str(uuid4()), document_id=str(uuid4()))
    # job.complete()
    uow.jobs.add(job)
    uow.commit()
    with pytest.raises(
        exceptions.InvalidJobStatusTransitionErrorDepr,
        match="Invalid status transition for job",
    ):
        kul_ocr.service_layer.services.jobs.retry_ocr_job(job.id, uow)


def test_retry_nonexisting_job_raises_not_found(uow):
    non_existing_job_id = uuid4()
    with pytest.raises(kul_ocr.adapters.database.repository.OCRJobNotFoundError):
        kul_ocr.service_layer.services.jobs.retry_ocr_job(str(non_existing_job_id), uow)
