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
    # TODO: Implement image loading
    # 1. Check if path exists, raise FileNotFoundError if not
    # 2. Try to open with Image.open()
    # 4. Return the opened image
    raise NotImplementedError("TODO: Implement load_image()")


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
    # TODO: Implement image saving
    # 1. Ensure parent directory exists: output_path.parent.mkdir(parents=True, exist_ok=True)
    # 2. Save image: image.save(output_path)
    # 3. Return output_path
    raise NotImplementedError("TODO: Implement save_image()")


def get_image_files(directory: Path) -> :
    #we want to specify what will this function return
    #and we know that it will return list of paths
    #soo...
    """Get all image files from a directory.

    Supported formats: .png, .jpg, .jpeg, .tiff, .bmp

    Args:
        directory: Directory to search

    Returns:
        List of Path objects for image files

    Raises:
        NotADirectoryError: If path is not a directory
    """
    # TODO: Implement image file discovery
    # 1. Check if directory exists and is a directory
    # 2. Use directory.glob() or directory.rglob() to find images
    # 3. Filter for supported extensions
    # 4. Return sorted list of paths
    raise NotImplementedError("TODO: Implement get_image_files()")
