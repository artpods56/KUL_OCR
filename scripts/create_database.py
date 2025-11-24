"""Database setup script for creating tables."""

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from kul_ocr.adapters.database import orm
from kul_ocr.config import app_config
from kul_ocr.entrypoints.dependencies import get_engine

from kul_ocr.utils.logger import setup_logging, Logger
from structlog import get_logger

setup_logging()

_ = load_dotenv()

logger: Logger = get_logger()


def create_database(database_uri: str | None = None) -> Engine:
    """Create database tables and return engine."""
    engine = get_engine(database_uri)
    orm.metadata.create_all(engine)
    return engine


def setup_database():
    """Setup database by starting mappers and creating tables."""
    logger.info("Running SQL Alchemy ORM mappers..")
    orm.start_mappers()

    logger.info("Fetching configuration..")
    database_uri = app_config.database_uri
    logger.info(f"Creating database at {database_uri}")

    engine = create_database(database_uri)
    logger.info("Database created successfully!")
    return engine


if __name__ == "__main__":
    _ = setup_database()
