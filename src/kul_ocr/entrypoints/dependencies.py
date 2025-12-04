from functools import lru_cache
from typing import Literal

from sqlalchemy.engine.base import Engine
from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm.session import Session, sessionmaker

from kul_ocr import config
from kul_ocr.adapters.storages import local
from kul_ocr.domain import ports
from kul_ocr.domain.ports import FileStorage
from kul_ocr.service_layer import uow
from kul_ocr.config import get_app_config

STORAGE_TYPES = Literal["local"]
SUPPORTED_STORAGE_TYPES: dict[str, type[FileStorage]] = {
    "local": local.LocalFileStorage,
}


@lru_cache
def get_config() -> config.AppConfig:
    """Retrieve the application configuration

    Returns:
        The cached AppConfig instance
    """
    return get_app_config()


@lru_cache
def get_file_storage() -> ports.FileStorage:
    """Get the configured file storage backend.

    Maps the configured storage type to the corresponding storage class
    and initializes it using the application configuration.

    Returns:
        An instance of the selected FileStorage implementation.

    Raises:
        NotImplementedError: If the configured storage type is not supported.
    """
    app_config = get_config()

    # The Mapping and Validation happens here now
    storage_class = SUPPORTED_STORAGE_TYPES.get(app_config.storage_type, None)

    if storage_class is None:
        raise NotImplementedError(
            f"Storage type '{app_config.storage_type}' is not implemented. ",
        )

    return storage_class.from_config(app_config)


@lru_cache
def get_uow() -> uow.AbstractUnitOfWork:
    """Get a Unit of Work instance using SQLAlchemy.

    Returns:
        An instance of SqlAlchemyUnitOfWork
    """
    return uow.SqlAlchemyUnitOfWork(
        session_factory=get_session_factory(),
    )


@lru_cache
def get_engine(database_uri: str | None = None) -> Engine:
    """Get a SQLAlchemy engine for database connection.

    Args:
        database_uri: Optional database URI. If None, uses the app configuration.

    Returns:
        A SQLAlchemy Engine instance configured with SERIALIZABLE isolation level.
    """
    app_config = get_config()
    if database_uri is None:
        database_uri = app_config.database_uri
    return create_engine(database_uri, isolation_level="SERIALIZABLE")


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Get SQLAlchemy session factory.

    This factory is used to generate session objects for database operations.
    If no engine is provided, the default engine from the application configuration is used.

    Args:
        engine: Optional SQLAlchemy Engine. Defaults to engine from get_engine().

    Returns:
        A SQLAlchemy sessionmaker bound to the provided engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


DEFAULT_SESSION_FACTORY = None
