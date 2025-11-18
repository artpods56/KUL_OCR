"""Image preprocessing functions for OCR quality improvement.

This module provides image enhancement functions that work on PIL Images.
All functions take a PIL Image and return a modified PIL Image.
"""

from PIL import Image, ImageEnhance, ImageFilter


def enhance_image(image: Image.Image) -> Image.Image:
    """Enhance image for better OCR results.

    Apply enhancements to improve OCR accuracy:
    - Convert to grayscale
    - Increase contrast
    - Sharpen
    - Denoise

    Args:
        image: PIL Image to enhance

    Returns:
        Enhanced PIL Image (grayscale)
    """
    # TODO: Implement image enhancement
    # 1. Convert to grayscale: image.convert('L')
    # 2. Enhance contrast: ImageEnhance.Contrast(img).enhance(1.5)
    # 3. Enhance sharpness: ImageEnhance.Sharpness(img).enhance(2.0)
    # 4. Apply denoising: img.filter(ImageFilter.MedianFilter(size=3))
    # 5. Return the enhanced image
    raise NotImplementedError("TODO: Implement enhance_image()")


def resize_image(image: Image.Image, scale_factor: float = 2.0) -> Image.Image:
    """Resize image by scale factor for better OCR on small text.

    Args:
        image: PIL Image to resize
        scale_factor: Multiplication factor for resizing (default: 2.0)

    Returns:
        Resized PIL Image

    Raises:
        ValueError: If scale_factor <= 0
    """
    # TODO: Implement image resizing
    # 1. Validate scale_factor > 0, raise ValueError if not
    # 2. Calculate new size: (width * scale_factor, height * scale_factor)
    # 3. Resize using Image.Resampling.LANCZOS
    # 4. Return resized image
    raise NotImplementedError("TODO: Implement resize_image()")


def binarize_image(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Convert image to binary (black and white) for OCR.

    Args:
        image: PIL Image to binarize
        threshold: Pixel value threshold (0-255)

    Returns:
        Binarized PIL Image (mode '1' - pure black and white)

    Raises:
        ValueError: If threshold not in range 0-255
    """
    # TODO: Implement image binarization
    # 1. Validate threshold in range 0-255
    # 2. Convert to grayscale if not already
    # 3. Apply threshold: img.point(lambda x: 0 if x < threshold else 255, '1')
    # 4. Return binarized image
    raise NotImplementedError("TODO: Implement binarize_image()")
