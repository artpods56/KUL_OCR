import io
from pathlib import Path

import pytest

from kul_ocr.adapters.storages.local import LocalFileStorage


class TestLocalFileStorage:
    @pytest.fixture
    def storage_root(self, tmp_path: Path) -> Path:
        """Create a temporary storage root directory."""
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        return storage_dir

    @pytest.fixture
    def storage(self, storage_root: Path) -> LocalFileStorage:
        """Create a LocalFileStorage instance."""
        return LocalFileStorage(storage_root=storage_root)

    @pytest.fixture
    def sample_content(self) -> bytes:
        """Sample file content for testing."""
        return b"Hello, World! This is a test file."

    @pytest.fixture
    def sample_stream(self, sample_content: bytes) -> io.BytesIO:
        """Create a BytesIO stream with sample content."""
        return io.BytesIO(sample_content)

    def test_init_sets_storage_root(self, storage_root: Path):
        storage = LocalFileStorage(storage_root=storage_root)

        assert storage.storage_root == storage_root

    def test_save_creates_file(
        self, storage: LocalFileStorage, sample_stream: io.BytesIO, tmp_path: Path
    ):
        file_path = tmp_path / "test_file.txt"

        storage.save(sample_stream, file_path)

        assert file_path.exists()
        assert file_path.is_file()

    def test_save_writes_correct_content(
        self,
        storage: LocalFileStorage,
        sample_stream: io.BytesIO,
        sample_content: bytes,
        tmp_path: Path,
    ):
        file_path = tmp_path / "test_file.txt"

        storage.save(sample_stream, file_path)

        with file_path.open("rb") as f:
            saved_content = f.read()
        assert saved_content == sample_content

    def test_save_creates_parent_directories(
        self, storage: LocalFileStorage, sample_stream: io.BytesIO, tmp_path: Path
    ):
        nested_path = tmp_path / "subdir1" / "subdir2" / "test_file.txt"
        nested_path.parent.mkdir(parents=True, exist_ok=True)

        storage.save(sample_stream, nested_path)

        assert nested_path.exists()

    def test_save_overwrites_existing_file(
        self, storage: LocalFileStorage, tmp_path: Path
    ):
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("Original content")

        new_content = b"New content"
        new_stream = io.BytesIO(new_content)
        storage.save(new_stream, file_path)

        with file_path.open("rb") as f:
            saved_content = f.read()
        assert saved_content == new_content

    def test_save_with_empty_stream(self, storage: LocalFileStorage, tmp_path: Path):
        file_path = tmp_path / "empty_file.txt"
        empty_stream = io.BytesIO(b"")

        storage.save(empty_stream, file_path)

        assert file_path.exists()
        assert file_path.stat().st_size == 0

    def test_save_with_large_file(self, storage: LocalFileStorage, tmp_path: Path):
        file_path = tmp_path / "large_file.bin"
        large_content = b"X" * (10 * 1024 * 1024)  # 10 MB
        large_stream = io.BytesIO(large_content)

        storage.save(large_stream, file_path)

        assert file_path.exists()
        assert file_path.stat().st_size == len(large_content)

    def test_save_stream_position_after_save(
        self, storage: LocalFileStorage, sample_stream: io.BytesIO, tmp_path: Path
    ):
        file_path = tmp_path / "test_file.txt"

        storage.save(sample_stream, file_path)

        # Stream position should be at the end after save
        assert sample_stream.tell() == len(sample_stream.getvalue())

    def test_save_with_binary_content(self, storage: LocalFileStorage, tmp_path: Path):
        file_path = tmp_path / "binary_file.bin"
        binary_content = bytes(range(256))
        binary_stream = io.BytesIO(binary_content)

        storage.save(binary_stream, file_path)

        with file_path.open("rb") as f:
            saved_content = f.read()
        assert saved_content == binary_content

    def test_load_reads_file(self, storage: LocalFileStorage, storage_root: Path):
        """Test that load method reads file content correctly."""
        file_path = storage_root / "test_file.txt"
        expected_content = b"Some content"
        file_path.write_bytes(expected_content)

        with storage.load(Path("test_file.txt")) as file:
            actual_content = file.read()

        assert actual_content == expected_content

    def test_delete_removes_file(self, storage: LocalFileStorage, storage_root: Path):
        """Test that delete method removes file correctly."""
        file_path = storage_root / "test_file.txt"
        file_path.write_text("Some content")

        assert file_path.exists()

        storage.delete(Path("test_file.txt"))

        assert not file_path.exists()
