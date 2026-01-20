from kul_ocr.entrypoints.schemas import JobResponse
import pytest
from uuid import uuid4, UUID
from kul_ocr.domain import model, exceptions
from kul_ocr.service_layer import services


def test_get_existing_ocr_job(uow):
    job = model.Job(id=str(uuid4()), document_id=str(uuid4()))
    uow.jobs.add(job)
    uow.commit

    response: JobResponse = JobResponse.from_domain(
        services.get_ocr_job(str(job.id), uow)
    )

    assert str(response.id) == job.id
    assert str(response.document_id) == job.document_id
    assert response.status == job.status


def test_get_nonexisting_ocr_job_raises(uow):
    non_existting_id = str(uuid4())
    with pytest.raises(exceptions.OCRJobNotFoundError):
        services.get_ocr_job(non_existting_id, uow)
