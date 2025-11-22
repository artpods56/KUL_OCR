"""I/O utilities for image loading and saving.

This module handles all file system operations, keeping them separate
from image processing logic.
"""
#sorry for stupid errors messages, but...I'm your father
from pathlib import Path

from PIL import Image
import os

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
    
    if not os.image_path.exists():
        raise FileNotFoundError("I can't do it anymore...without a file I can be myself.")
    try:
        opened_image=Image.open(image_path)
        opened_image.verify()
        opened_image=Image.open(image_path)
        return opened_image
    except (IOError, SyntaxError) as e:
        raise(f"I can't open a door named {e}")


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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def get_image_files(directory: Path) -> list[Path]:
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
    if not directory.is_dir():
        raise NotADirectoryError(f"I fear no man, but that thing...{directory} is not a directory")
    supported_formats=('.png','.jpg','.jpeg', '.tiff', '.bmp')
    images_paths=[]
    for file in directory.rglob("*"):
        if file.suffix.lower() in supported_formats:
            images_paths.append(file)
    return sorted(images_paths)