import io
import os
import pathlib
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self, final, override

from ocr_kul import config
from ocr_kul.domain import exceptions, ports


@final
class LocalFileStorage(ports.FileStorage):
    def _construct_full_path(self, file_path: pathlib.Path) -> pathlib.Path:
        return self.storage_root / file_path

    def __init__(self, storage_root: pathlib.Path):
        self.storage_root = storage_root

    @override
    @classmethod
    def from_config(cls, app_config: config.AppConfig) -> Self:
        return cls(storage_root=app_config.storage_root)

    @override
    def save(self, stream: ports.FileStreamProtocol, file_path: pathlib.Path) -> None:
        full_file_path = self._construct_full_path(file_path)

        try:
            with full_file_path.open("wb") as dest:
                shutil.copyfileobj(stream, dest)
        except OSError as e:
            raise exceptions.FileUploadError(
                f"Failed to save file {full_file_path} to the file system: {e}"
            ) from e

    @override
    @contextmanager
    def load(self, file_path: pathlib.Path) -> Iterator[ports.FileStreamProtocol]:
        full_file_path = self._construct_full_path(file_path)

        try:
            file = io.open(full_file_path, "rb")
        except FileNotFoundError as e:
            raise exceptions.FileUploadError(
                f"Could not find file {full_file_path}: {e}"
            )
        except OSError as e:
            raise exceptions.FileDownloadError(
                f"Failed to download file {full_file_path} from the file system: {e}"
            ) from e

        try:
            yield file
        finally:
            file.close()

    @override
    def delete(self, file_path: pathlib.Path) -> None:
        full_file_path = self._construct_full_path(file_path)

        try:
            os.remove(full_file_path)
        except OSError as e:
            raise exceptions.FileDownloadError(
                f"Failed to remove file {full_file_path}: {e}"
            )
