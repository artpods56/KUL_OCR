import os
from pathlib import Path

from dotenv import load_dotenv

from ocr_kul.utils.shared import REPO_ROOT

load_dotenv()


def get_sqlite3_uri() -> str:
    db_path_env = os.environ.get("SQLITE_DB_PATH", None)
    if db_path_env is None:
        raise RuntimeError("SQLITE_DB_PATH is not set")

    db_path = Path(db_path_env)
    if db_path.is_absolute():
        return f"sqlite:///{db_path}"
    else:
        return f"sqlite:///{REPO_ROOT / db_path}"
