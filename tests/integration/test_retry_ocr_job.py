"""Integration tests for OCR Job retry endpoint.

These tests use a real SQLite database and test the full request/response cycle.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from kul_ocr.adapters.database import orm
from kul_ocr.domain.enums import JobStatus
from kul_ocr.entrypoints import dependencies
from kul_ocr.entrypoints.api import app
from kul_ocr.service_layer.uow import SqlAlchemyUnitOfWork
from tests import factories


@pytest.fixture(scope="function")
def integration_engine():
    """Create a shared in-memory SQLite database for integration tests.

    Uses StaticPool to ensure the same connection is reused across all sessions,
    which is required for in-memory SQLite databases to share data.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    orm.start_mappers()
    orm.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def integration_session_factory(integration_engine) -> sessionmaker[Session]:
    """Create a session factory bound to the test database."""
    return sessionmaker(bind=integration_engine)


@pytest.fixture(scope="function")
def override_dependencies(integration_session_factory) -> Iterator[None]:
    """Override FastAPI dependencies to use the test database."""

    def get_test_uow():
        return SqlAlchemyUnitOfWork(session_factory=integration_session_factory)

    app.dependency_overrides[dependencies.get_uow] = get_test_uow
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def integration_client(override_dependencies) -> AsyncClient:
    """Create an async client that uses the test database."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_retry_failed_job_endpoint(
    integration_client: AsyncClient,
    integration_session_factory: sessionmaker[Session],
):
    """Test that POST /ocr/jobs/{job_id}/retry creates a new job for a failed job."""
    # Arrange - create a document and failed job in the database
    document = factories.generate_document_without_file()
    failed_job = factories.generate_ocr_job(status=JobStatus.PENDING)
    failed_job.document_id = document.id
    failed_job.update_status(JobStatus.PROCESSING)
    failed_job.update_status(JobStatus.FAILED, error_message="Test failure")

    # Store values before committing (to avoid detached instance issues)
    failed_job_id = failed_job.id
    document_id = document.id

    uow = SqlAlchemyUnitOfWork(session_factory=integration_session_factory)
    with uow:
        uow.documents.add(document)
        uow.jobs.add(failed_job)
        uow.commit()

    # Act
    response = await integration_client.post(f"/ocr/jobs/{failed_job_id}/retry")

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == JobStatus.PENDING.value
    assert data["id"] != failed_job_id  # Should be a new job
    assert data["document_id"] == document_id


@pytest.mark.asyncio
async def test_retry_non_failed_job_endpoint_returns_400(
    integration_client: AsyncClient,
    integration_session_factory: sessionmaker[Session],
):
    """Test that POST /ocr/jobs/{job_id}/retry returns 400 for non-failed jobs."""
    # Arrange - create a document and completed job
    document = factories.generate_document_without_file()
    completed_job = factories.generate_ocr_job(status=JobStatus.PENDING)
    completed_job.document_id = document.id
    completed_job.update_status(JobStatus.PROCESSING)
    completed_job.update_status(JobStatus.COMPLETED)

    # Store values before committing
    completed_job_id = completed_job.id

    uow = SqlAlchemyUnitOfWork(session_factory=integration_session_factory)
    with uow:
        uow.documents.add(document)
        uow.jobs.add(completed_job)
        uow.commit()

    # Act
    response = await integration_client.post(f"/ocr/jobs/{completed_job_id}/retry")

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "cannot transition" in data["detail"].lower()


@pytest.mark.asyncio
async def test_retry_nonexistent_job_endpoint_returns_404(
    integration_client: AsyncClient,
):
    """Test that POST /ocr/jobs/{job_id}/retry returns 404 for non-existent job."""
    # Arrange
    fake_id = str(uuid4())

    # Act
    response = await integration_client.post(f"/ocr/jobs/{fake_id}/retry")

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "ocr job" in data["detail"].lower()
