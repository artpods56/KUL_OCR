"""I/O utilities for image loading and saving.

This module handles all file system operations, keeping them separate
from image processing logic.
"""

from pathlib import Path

from PIL import Image


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
    # 1. Check if path exists, raise FileNotFoundError if not
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # 2. Try to open with Image.open()
    try:
        image = Image.open(image_path)
    except Exception as e:
        raise ValueError(f"Cannot open image file: {image_path}") from e

    # 3. Return the opened image
    return image


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
    # 1. Ensure parent directory exists: output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. Save image: image.save(output_path)
    try:
        image.save(output_path)
    except Exception as e:
        raise IOError(f"Cannot save image to: {output_path}") from e

    # 3. Return output_path
    return output_path


def get_image_files(directory: Path) -> list[Path]:
    """Get all image files from a directory.

    Supported formats: .png, .jpg, .jpeg, .tiff, .bmp

    Args:
        directory: Directory to search

    Returns:
        List of Path objects for image files

    Raises:
        NotADirectoryError: If path is not a directory
    """
    # 1. Check if directory exists and is a directory
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    # 2. Use directory.glob() or directory.rglob() to find images
    directory_files = directory.rglob("*")

    # 3. Filter for supported extensions
    image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
    image_files = [f for f in directory_files if f.suffix.lower() in image_extensions]

    # 4. Return sorted list of paths
    return sorted(image_files)
