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
    """Type-safe fake that implements the FileStorage protocol."""

    saved_files: list[tuple[str, bytes]] = field(default_factory=list)

    @classmethod
    @override
    def from_config(cls, app_config: config.AppConfig) -> Self:
        return cls()

    @override
    def save(self, stream: FileStreamProtocol, file_path: pathlib.Path) -> None:
        content = stream.read()
        self.saved_files.append((str(file_path), content))

    @override
    @contextmanager
    def load(self, file_path: pathlib.Path) -> Iterator[FileStreamProtocol]:
        for path, content in self.saved_files:
            if path == str(file_path):
                yield BytesIO(content)
                return
        raise FileNotFoundError(f"File not found: {file_path}")

    @override
    def delete(self, file_path: pathlib.Path) -> None:
        self.saved_files = [
            (path, content)
            for path, content in self.saved_files
            if path != str(file_path)
        ]

    @property
    def save_call_count(self) -> int:
        return len(self.saved_files)
