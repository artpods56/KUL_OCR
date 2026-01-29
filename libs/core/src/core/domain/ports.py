import abc
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol, Self, runtime_checkable

from PIL import Image

from core import config
from core.domain import enums, model, structs


@runtime_checkable
class FileStreamProtocol(Protocol):
    # name: str
    def read(self, size: int = -1, /) -> bytes: ...
    def seek(self, offset: int, whence: int = 0, /) -> int: ...
    def tell(self) -> int: ...


class OCREngine(abc.ABC):
    SUPPORTED_FILE_TYPES: set[enums.FileType]

    @abc.abstractmethod
    def process_image(self, image: Image.Image) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def engine_name(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def engine_version(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def supports_file_type(self, file_type: enums.FileType) -> bool:
        raise NotImplementedError


class DocumentLoader(abc.ABC):
    """Port for loading document content as a stream of images."""

    @abc.abstractmethod
    def load_pages(
        self, doc_input: structs.DocumentInput
    ) -> Iterator[structs.PageInput]:
        """
        Lazily loads pages from a document.
        Returns an Iterator to prevent loading entire PDFs into memory.
        """
        raise NotImplementedError


class FileStorage(abc.ABC):
    @abc.abstractmethod
    def save(self, stream: FileStreamProtocol, file_path: pathlib.Path) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def move(self, source_path: pathlib.Path, destination_path: pathlib.Path) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    @contextmanager
    def load(self, file_path: pathlib.Path) -> Iterator[FileStreamProtocol]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, file_path: pathlib.Path) -> None:
        raise NotImplementedError
