from ocr_kul.adapters import orm
from ocr_kul.service_layer.config import get_sqlite3_uri


def setup_database():
    print("Running SQL Alchemy ORM mappers..")
    orm.start_mappers()

    print("Fetching configuration..")
    database_uri = get_sqlite3_uri()

    print(f"Creating database at {database_uri}")
    _ = orm.create_database(database_uri)


if __name__ == "__main__":
    setup_database()
