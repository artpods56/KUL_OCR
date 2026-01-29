"""Database setup script for creating tables."""

from dotenv import load_dotenv
from sqlalchemy.engine import Engine

from core.adapters.database import orm
from core.config import get_app_config
from dependencies import get_engine

from core.utils.logger import get_logger, setup_logging

setup_logging()

_ = load_dotenv()

logger = get_logger(__name__)


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
    database_uri = get_app_config().database_uri
    logger.info(f"Creating database at {database_uri}")

    engine = create_database(database_uri)
    logger.info("Database created successfully!")
    return engine


if __name__ == "__main__":
    _ = setup_database()
