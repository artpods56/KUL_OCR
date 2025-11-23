import pytest
from httpx import ASGITransport, AsyncClient

from ocr_kul.entrypoints.api import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
