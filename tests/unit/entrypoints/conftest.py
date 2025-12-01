import pytest

from typing import Literal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from kul_ocr.entrypoints.api import app


@pytest.fixture
def anyio_backend() -> str:
    """Specifies the backend to use for asynchronous tests."""
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def client(anyio_backend: Literal["asyncio"]):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
