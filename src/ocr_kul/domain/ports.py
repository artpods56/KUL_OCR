import abc
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol, Self, runtime_checkable

from PIL import Image

from ocr_kul import config
from ocr_kul.domain import model, structs


@runtime_checkable
class FileStreamProtocol(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...
    def seek(self, offset: int, whence: int = 0, /) -> int: ...
    def tell(self) -> int: ...


class OCREngine(abc.ABC):
    SUPPORTED_FILE_TYPES: set[model.FileType]

    @abc.abstractmethod
    def _initialize_engine(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _validate_engine(self) -> None:
        raise NotImplementedError

    def _process_image(self, image: Image.Image) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def process_document(self, document: model.Document) -> model.OCRValueTypes:
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
    def supports_file_type(self, file_type: model.FileType) -> bool:
        raise NotImplementedError


class DocumentLoader(abc.ABC):
    """Port for loading document content as a stream of images."""

    @abc.abstractmethod
    def load_pages(self, document: model.Document) -> Iterator[structs.PageInput]:
        """
        Lazily loads pages from a document.
        Returns an Iterator to prevent loading entire PDFs into memory.
        """
        raise NotImplementedError


class FileStorage(abc.ABC):
    storage_root: pathlib.Path

    @classmethod
    @abc.abstractmethod
    def from_config(cls, app_config: config.AppConfig) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, stream: FileStreamProtocol, file_path: pathlib.Path) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    @contextmanager
    def load(self, file_path: pathlib.Path) -> Iterator[FileStreamProtocol]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, file_path: pathlib.Path) -> None:
        raise NotImplementedError
