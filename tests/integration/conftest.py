import tempfile
from pathlib import Path
from typing import Callable, Generator, Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker, Session

from ocr_kul.adapters.database import orm
from ocr_kul.service_layer.uow import SqlAlchemyUnitOfWork


@pytest.fixture(scope="function")
def test_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = Path(tmp_file.name)

    yield db_path

    # cleanup: remove the test database after the test
    if db_path.exists():
        db_path.unlink()


@pytest.fixture(scope="function")
def test_engine(test_db_path: Path) -> Generator[Engine, None, None]:
    """Create a test database engine"""
    db_uri = f"sqlite:///{test_db_path}"
    engine = create_engine(db_uri, isolation_level="SERIALIZABLE")

    # Start mappers if not already started
    try:
        orm.start_mappers()
    except Exception:
        # Mappers already started
        pass

    # Create all tables
    orm.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture(scope="function")
def test_session_factory(test_engine: Engine):
    """Create a session factory for testing"""
    return sessionmaker(bind=test_engine)


@pytest.fixture(scope="function")
def uow(test_session_factory: sessionmaker[Session]) -> SqlAlchemyUnitOfWork:
    """Create a Unit of Work for integration testing"""
    return SqlAlchemyUnitOfWork(session_factory=test_session_factory)


@pytest.fixture(scope="function")
def test_session(
    test_session_factory: Callable[[], Session],
) -> Generator[Session, Any, None]:
    """Create a test database session"""
    session: Session = test_session_factory()

    yield session

    # Cleanup
    session.close()
