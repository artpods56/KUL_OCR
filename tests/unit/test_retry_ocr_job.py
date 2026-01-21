from kul_ocr.entrypoints.schemas import JobResponse
import pytest
from uuid import uuid4
from kul_ocr.domain import model, exceptions
from kul_ocr.service_layer import services


def test_retry_failed_job_creates_new_pending_job(uow):
    failed_job = model.Job(id=str(uuid4()), document_id=str(uuid4()))
    failed_job.fail("OCR error")
    uow.jobs.add(failed_job)
    uow.commit()

    response: JobResponse = services.retry_ocr_job(failed_job.id, uow)
    assert str(response.id) != failed_job.id
    assert str(response.document_id) == failed_job.document_id
    assert response.status == model.JobStatus.PENDING

    original_job = uow.jobs.get(failed_job.id)
    assert original_job.status == model.JobStatus.FAILED


def test_retry_non_failed_job_raises_error(uow):
    job = model.Job(id=str(uuid4()), document_id=str(uuid4()))
    # job.complete()
    uow.jobs.add(job)
    uow.commit()
    with pytest.raises(
        exceptions.InvalidJobStatusTransitionError,
        match="Invalid status transition for job",
    ):
        services.retry_ocr_job(job.id, uow)


def test_retry_nonexisting_job_raises_not_found(uow):
    non_existing_job_id = uuid4()
    with pytest.raises(exceptions.OCRJobNotFoundError):
        services.retry_ocr_job(str(non_existing_job_id), uow)
