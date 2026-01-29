from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from typing import final, override

from core.domain import exceptions, ports


@final
class LocalFileStorage(ports.FileStorage):
    """
    Local filesystem storage implementation.

    Provides atomic writes via temporary files and basic path traversal protection.
    """

    def __init__(self, storage_root: pathlib.Path) -> None:
        self._storage_root = storage_root.resolve()
        self._storage_root.mkdir(parents=True, exist_ok=True)

    @property
    def storage_root(self) -> pathlib.Path:
        """Return the storage root directory."""
        return self._storage_root

    def _resolve_relative(self, relative_path: pathlib.Path) -> pathlib.Path:
        """
        Resolve a relative path within storage root.

        Guards against path traversal by rejecting absolute paths and '..' components,
        then verifying the resolved path stays within the storage root.
        """
        if relative_path.is_absolute():
            raise exceptions.StorageSecurityError(
                f"Absolute paths are forbidden: {relative_path}"
            )

        if ".." in relative_path.parts:
            raise exceptions.StorageSecurityError(
                f"Path traversal detected: {relative_path}"
            )

        full_path = (self._storage_root / relative_path).resolve()

        if not full_path.is_relative_to(self._storage_root):
            raise exceptions.StorageSecurityError(
                f"Resolved path escapes storage root: {relative_path}"
            )

        return full_path

    @override
    def save(self, stream: ports.FileStreamProtocol, file_path: pathlib.Path) -> None:
        """
        Save a stream to storage using atomic write.

        Writes to a temporary file first, then atomically replaces the target.
        This prevents partial writes if the process crashes.
        """
        target = self._resolve_relative(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in same directory to ensure atomic replace works
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        tmp_path = pathlib.Path(tmp_name)

        try:
            with os.fdopen(fd, "wb") as f:
                shutil.copyfileobj(stream, f)

            # Atomic replacement on POSIX systems
            os.replace(tmp_path, target)

        except OSError as e:
            # Clean up temp file on failure
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

            raise exceptions.StorageIOError(
                f"Failed to save file to {file_path}: {e}"
            ) from e

    @override
    @contextmanager
    def load(self, file_path: pathlib.Path) -> Iterator[ports.FileStreamProtocol]:
        """Load a file from storage as a context manager."""
        full_path = self._resolve_relative(file_path)

        if not full_path.is_file():
            raise exceptions.StorageFileNotFoundError(
                f"File does not exist: {file_path}"
            )

        try:
            with open(full_path, "rb") as f:
                yield f
        except OSError as e:
            raise exceptions.StorageIOError(
                f"Failed to read file at {file_path}: {e}"
            ) from e

    @override
    def move(self, source_path: pathlib.Path, destination_path: pathlib.Path) -> None:
        """
        Move a file between locations.

        Atomic within the same filesystem. Idempotent: if source is gone
        but destination exists, assumes move already completed.
        """
        src = self._resolve_relative(source_path)
        dst = self._resolve_relative(destination_path)

        # Idempotency check for retry safety
        if not src.exists() and dst.exists():
            return

        if not src.exists():
            raise exceptions.StorageFileNotFoundError(
                f"Source file does not exist: {source_path}"
            )

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.move(str(src), str(dst))
        except OSError as e:
            raise exceptions.StorageIOError(
                f"Failed to move {source_path} to {destination_path}: {e}"
            ) from e

    @override
    def delete(self, file_path: pathlib.Path) -> None:
        """Delete a file from storage. Idempotent: no error if file doesn't exist."""
        full_path = self._resolve_relative(file_path)

        if not full_path.exists():
            return

        try:
            full_path.unlink()
        except OSError as e:
            raise exceptions.StorageIOError(
                f"Failed to delete file at {file_path}: {e}"
            ) from e
