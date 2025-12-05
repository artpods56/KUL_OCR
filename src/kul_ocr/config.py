from pathlib import Path
from typing import Literal
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from kul_ocr.utils.misc import nobeartype
from kul_ocr.utils.shared import REPO_ROOT

_ = load_dotenv()

SUPPORTED_DATABASES = Literal["sqlite", "mysql", "postgres"]


@nobeartype
class DatabaseSettings(BaseSettings):
    db_scheme: SUPPORTED_DATABASES
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: str | None = None
    db_name: str | None = None
    db_path: str | None = None  # for sqlite

    @field_validator("db_path", mode="before")
    def validate_sqlite_path(cls, value: str, info: ValidationInfo):
        if "db_scheme" in info.data:
            if not value and info.data["db_scheme"] == "sqlite":
                raise ValueError(
                    f"Field `{info.field_name}` must be set with db_scheme=`{info.data['db_scheme']}`"
                )
        return value

    @field_validator(
        "db_user", "db_password", "db_host", "db_port", "db_name", mode="before"
    )
    def validate_network_fields(cls, value: str, info: ValidationInfo):
        if "db_scheme" in info.data:
            if not value and info.data["db_scheme"] != "sqlite":
                raise ValueError(
                    f"Field `{info.field_name}` must be set with db_scheme=`{info.data['db_scheme']}`"
                )
        return value

    @property
    def database_uri(self) -> str:
        if self.db_scheme == "sqlite":
            return f"sqlite:///{self.db_path}"
        else:
            return f"{self.db_scheme}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class AppConfig(DatabaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KUL_OCR_", env_file=REPO_ROOT / ".env", extra="allow"
    )

    storage_type: str
    storage_root: Path

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    logs_dir: Path


@lru_cache()
def get_app_config():
    return AppConfig()  # pyright: ignore[reportCallIssue]
