import core.adapters.database.repository
import core.service_layer.services.jobs
from backend.schemas import JobResponse
import pytest
from uuid import uuid4
from core.domain import model


def test_get_existing_ocr_job(uow):
    job = model.Job(id=str(uuid4()), document_id=str(uuid4()))
    uow.jobs.add(job)
    uow.commit

    response: JobResponse = JobResponse.from_dto(
        core.service_layer.services.jobs.get_ocr_job(str(job.id), uow)
    )

    assert str(response.id) == job.id
    assert str(response.document_id) == job.document_id
    assert response.status == job.status


def test_get_nonexisting_ocr_job_raises(uow):
    non_existting_id = str(uuid4())
    with pytest.raises(core.adapters.database.repository.OCRJobNotFoundError):
        core.service_layer.services.jobs.get_ocr_job(non_existting_id, uow)
