"""Tests for I/O utilities."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from ocr_kul.io_utils import get_image_files, load_image, save_image


def test_load_image_raises_on_missing_file():
    """load_image must raise FileNotFoundError for non-existent files."""
    nonexistent = Path("nonexistent.png")

    with pytest.raises(FileNotFoundError):
        load_image(nonexistent)


def test_load_image_returns_pil_image():
    """load_image must return a PIL Image object."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        # Create a test image
        img = Image.new("RGB", (100, 100), color="white")
        img.save(tmp.name)
        test_path = Path(tmp.name)

        try:
            result = load_image(test_path)
            assert isinstance(result, Image.Image)
        except NotImplementedError:
            pytest.skip("load_image() not implemented")
        finally:
            test_path.unlink()


def test_load_image_raises_on_invalid_image():
    """load_image must raise ValueError for invalid image files."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        # Write non-image data
        tmp.write(b"This is not an image")
        tmp.flush()
        test_path = Path(tmp.name)

        try:
            with pytest.raises(ValueError):
                load_image(test_path)
        finally:
            test_path.unlink()


def test_save_image_creates_file():
    """save_image must create the output file."""
    test_img = Image.new("RGB", (100, 100), color="red")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test.png"

        try:
            result = save_image(test_img, output_path)

            assert output_path.exists(), "Output file must be created"
            assert result == output_path, "Must return the output path"
        except NotImplementedError:
            pytest.skip("save_image() not implemented")


def test_save_image_creates_parent_directories():
    """save_image must create parent directories if they don't exist."""
    test_img = Image.new("RGB", (50, 50), color="blue")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "subdir" / "nested" / "test.png"

        try:
            save_image(test_img, output_path)

            assert output_path.exists()
            assert output_path.parent.exists()
        except NotImplementedError:
            pytest.skip("save_image() not implemented")


def test_get_image_files_raises_on_non_directory():
    """get_image_files must raise NotADirectoryError for non-directories."""
    not_a_dir = Path("some_file.txt")

    with pytest.raises(NotADirectoryError):
        get_image_files(not_a_dir)


def test_get_image_files_finds_images():
    """get_image_files must find all supported image formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)

        # Create test images
        (dir_path / "test1.png").touch()
        (dir_path / "test2.jpg").touch()
        (dir_path / "test3.jpeg").touch()
        (dir_path / "test4.tiff").touch()
        (dir_path / "not_image.txt").touch()

        try:
            result = get_image_files(dir_path)

            assert len(result) == 4, "Should find 4 image files"
            assert all(isinstance(p, Path) for p in result)

            # Should not include txt file
            assert not any(p.suffix == ".txt" for p in result)
        except NotImplementedError:
            pytest.skip("get_image_files() not implemented")


def test_get_image_files_returns_sorted_list():
    """get_image_files should return a sorted list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)

        # Create images in non-alphabetical order
        (dir_path / "zebra.png").touch()
        (dir_path / "apple.png").touch()
        (dir_path / "banana.png").touch()

        try:
            result = get_image_files(dir_path)

            filenames = [p.name for p in result]
            assert filenames == sorted(filenames), "Results should be sorted"
        except NotImplementedError:
            pytest.skip("get_image_files() not implemented")
