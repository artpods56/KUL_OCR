"""I/O utilities for image loading and saving.

This module handles all file system operations, keeping them separate
from image processing logic.
"""

from pathlib import Path

from PIL import Image, UnidentifiedImageError


def load_image(image_path: Path) -> Image.Image:
    """Load an image from disk.

    Args:
        image_path: Path to the image file

    Returns:
        PIL Image object

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If file is not a valid image

    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        with Image.open(image_path) as img:
            image = img.copy()
        return image
    except UnidentifiedImageError as e:
        raise ValueError(f"Invalid image file: {image_path}") from e
    except Exception as e:
        raise ValueError(f"Failed to load image: {image_path}") from e


def save_image(image: Image.Image, output_path: Path) -> Path:
    """Save an image to disk.

    Args:
        image: PIL Image to save
        output_path: Path where image should be saved

    Returns:
        Path to the saved image

    Raises:
        IOError: If image cannot be saved


    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def get_image_files(directory: Path) -> list[Path]:
    """Get all image files from a directory.

    Supported formats: .png, .jpg, .jpeg, .tiff, .bmp

    Args:
        directory: Directory to search

    Returns:
        List of Path objects for image files, sorted alphabetically

    Raises:
        NotADirectoryError: If path is not a directory

    """
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    supported_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

    image_files = [
        file_path
        for file_path in directory.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions
    ]

    return sorted(image_files)
