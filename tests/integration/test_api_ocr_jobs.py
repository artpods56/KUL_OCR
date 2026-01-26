"""Integration tests for OCR Jobs API endpoints.

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
async def test_get_existing_ocr_job_endpoint(
    integration_client: AsyncClient,
    integration_session_factory: sessionmaker[Session],
):
    """Test that GET /ocr/jobs/{job_id} returns job details for existing job."""
    # Arrange - create a document and job in the database
    document = factories.generate_document_without_file()
    job = factories.generate_ocr_job(status=JobStatus.PENDING)
    job.document_id = document.id

    # Store IDs before committing (to avoid detached instance issues)
    job_id = job.id
    document_id = document.id
    job_status = job.status.value

    uow = SqlAlchemyUnitOfWork(session_factory=integration_session_factory)
    with uow:
        uow.documents.add(document)
        uow.jobs.add(job)
        uow.commit()

    # Act
    response = await integration_client.get(f"/ocr/jobs/{job_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["document_id"] == document_id
    assert data["status"] == job_status


@pytest.mark.asyncio
async def test_get_nonexistent_ocr_job_endpoint_returns_404(
    integration_client: AsyncClient,
):
    """Test that GET /ocr/jobs/{job_id} returns 404 for non-existent job."""
    # Arrange
    fake_id = str(uuid4())

    # Act
    response = await integration_client.get(f"/ocr/jobs/{fake_id}")

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
