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
    return get_app_config()


@lru_cache
def get_file_storage() -> ports.FileStorage:
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
    return uow.SqlAlchemyUnitOfWork(
        session_factory=get_session_factory(),
    )


@lru_cache
def get_engine(database_uri: str | None = None) -> Engine:
    """Get SQLAlchemy engine for database connection."""
    app_config = get_config()
    if database_uri is None:
        database_uri = app_config.database_uri
    return create_engine(database_uri, isolation_level="SERIALIZABLE")


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Get SQLAlchemy session factory."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


DEFAULT_SESSION_FACTORY = None

