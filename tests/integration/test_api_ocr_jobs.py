import pytest
import asyncio
from uuid import uuid4
from httpx import AsyncClient

from kul_ocr.domain.model import JobStatus
from tests.fakes.uow import FakeUnitOfWork
from tests import factories
from kul_ocr.entrypoints.api import app

#nie wiem jak to zrobić by nie było error

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_get_existing_ocr_job_endpoint(client: AsyncClient, uow: FakeUnitOfWork):
    # Arrange
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    uow.jobs.add(job)

    # Act
    response = await client.get(f"/ocr/jobs/{job.id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job.id
    assert data["document_id"] == job.document_id
    assert data["status"] == job.status.value

@pytest.mark.asyncio
async def test_get_nonexistent_ocr_job_endpoint_returns_404(client: AsyncClient):
    # Arrange
    fake_id = str(uuid4())

    # Act
    response = await client.get(f"/ocr/jobs/{fake_id}")

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
