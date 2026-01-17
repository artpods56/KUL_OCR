import pytest
import asyncio
from uuid import uuid4
from httpx import AsyncClient

from kul_ocr.domain.model import JobStatus
from tests.fakes.uow import FakeUnitOfWork
from tests import factories

#nie wiem jak to zrobić by nie było error

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_retry_failed_job_endpoint(client: AsyncClient, uow: FakeUnitOfWork):
    failed_job = factories.generate_ocr_job(status=JobStatus.FAILED)
    uow.jobs.add(failed_job)

    response = await client.post(f"/jobs/{failed_job.id}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == JobStatus.PENDING.value
    assert data["id"] != failed_job.id


@pytest.mark.asyncio
async def test_retry_non_failed_job_endpoint_returns_400(
    client: AsyncClient, uow: FakeUnitOfWork
):
    completed_job = factories.generate_ocr_job(status=JobStatus.COMPLETED)
    uow.jobs.add(completed_job)

    response = await client.post(f"/jobs/{completed_job.id}/retry")
    assert response.status_code == 400
    data = response.json()
    assert "only failed jobs can be retried" in data["detail"]


@pytest.mark.asyncio
async def test_retry_nonexistent_job_endpoint_returns_404(
    client: AsyncClient, uow: FakeUnitOfWork
):
    fake_id = str(uuid4())
    response = await client.post(f"/jobs/{fake_id}/retry")
    assert response.status_code == 404
    data = response.json()
    assert "OCR Job" in data["detail"]
