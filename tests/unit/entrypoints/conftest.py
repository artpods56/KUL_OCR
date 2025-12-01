import pytest
from collections.abc import AsyncGenerator
from typing import Literal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from kul_ocr.entrypoints.api import app
from kul_ocr.utils.misc import nobeartype


@pytest.fixture
def anyio_backend() -> str:
    """Specifies the backend to use for asynchronous tests."""
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
@nobeartype
async def client(
    anyio_backend: Literal["asyncio"],
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
