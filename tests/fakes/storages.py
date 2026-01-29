from contextlib import contextmanager
from io import BytesIO
import pathlib
from dataclasses import dataclass, field
from collections.abc import Iterator
from typing import override, Self

from core import config
from core.domain import ports
from core.domain.ports import FileStreamProtocol


@dataclass
class FakeFileStorage(ports.FileStorage):
    """Simple in-memory Fake storage used in tests."""

    files: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    def from_config(cls, _app_config: config.AppConfig) -> Self:
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
    def move(self, source_path: pathlib.Path, destination_path: pathlib.Path) -> None:
        bytes = self.files[str(source_path)]
        del self.files[str(source_path)]
        self.files[str(destination_path)] = bytes

    @override
    def delete(self, file_path: pathlib.Path) -> None:
        _ = self.files.pop(str(file_path), None)

    @property
    def save_call_count(self) -> int:
        return len(self.files)
