import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.api import app

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
