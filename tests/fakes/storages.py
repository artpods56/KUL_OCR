from contextlib import contextmanager
from io import BytesIO
import pathlib
from dataclasses import dataclass, field
from typing import Iterator, override, Self

from kul_ocr import config
from kul_ocr.domain import ports
from kul_ocr.domain.ports import FileStreamProtocol


@dataclass
class FakeFileStorage(ports.FileStorage):
    """Simple in-memory Fake storage used in tests."""

    files: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    @override
    def from_config(cls, app_config: config.AppConfig) -> Self:
        return cls()

    @override
    def save(self, stream: FileStreamProtocol, file_path: pathlib.Path) -> None:
        content = stream.read()
        self.files[str(file_path)] = content

    @override
    @contextmanager
    def load(self, file_path: pathlib.Path) -> Iterator[FileStreamProtocol]:
        path = str(file_path)
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {file_path}")

        yield BytesIO(self.files[path])

    @override
    def delete(self, file_path: pathlib.Path) -> None:
        self.files.pop(str(file_path), None)

    @property
    def save_call_count(self) -> int:
        return len(self.files)
