from typing import Literal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from kul_ocr.entrypoints.api import app


@pytest_asyncio.fixture(autouse=True)
async def client(anyio_backend: Literal["trio", "asyncio"]):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
