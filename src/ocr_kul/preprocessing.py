"""Image preprocessing functions for OCR quality improvement.

This module provides image enhancement functions that work on PIL Images.
All functions take a PIL Image and return a modified PIL Image.
"""

from typing import Union

from PIL import Image, ImageEnhance, ImageFilter


def enhance_image(image: Image.Image) -> Image.Image:
    """Enhance image for better OCR results.

    Apply enhancements to improve OCR accuracy:
    - Convert to grayscale
    - Increase contrast (factor 1.5)
    - Sharpen (factor 2.0)
    - Denoise (Median Filter size 3)

    Args:
        image: PIL Image to enhance

    Returns:
        Enhanced PIL Image (grayscale)
    """
    enhanced_img = image.convert("L")

    contrast_enhancer = ImageEnhance.Contrast(enhanced_img)
    enhanced_img = contrast_enhancer.enhance(1.5)

    sharpness_enhancer = ImageEnhance.Sharpness(enhanced_img)
    enhanced_img = sharpness_enhancer.enhance(2.0)

    enhanced_img = enhanced_img.filter(ImageFilter.MedianFilter(size=3))

    return enhanced_img


def resize_image(
    image: Image.Image, scale_factor: Union[int, float] = 2.0
) -> Image.Image:
    """Resize image by scale factor for better OCR on small text.

    Args:
        image: PIL Image to resize
        scale_factor: Multiplication factor for resizing (default: 2.0).
                      Uses LANCZOS resampling for high quality.

    Returns:
        Resized PIL Image

    Raises:
        ValueError: If scale_factor is non-positive (<= 0).
    """
    if scale_factor <= 0:
        raise ValueError(f"Scale factor must be positive, got {scale_factor}")

    width, height = image.size
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    try:
        resample_method = Image.Resampling.LANCZOS
    except AttributeError:
        resample_method = Image.LANCZOS

    resized_image = image.resize((new_width, new_height), resample=resample_method)

    return resized_image


def binarize_image(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Convert image to binary (black and white) for OCR.

    Args:
        image: PIL Image to binarize
        threshold: Pixel value threshold (0-255). Pixels below this value become black (0).

    Returns:
        Binarized PIL Image (mode '1' - pure black and white)

    Raises:
        ValueError: If threshold not in range 0-255.
    """
    if not 0 <= threshold <= 255:
        raise ValueError(
            f"Threshold must be between 0 and 255 (inclusive), got {threshold}"
        )

    if image.mode != "L":
        img_gray = image.convert("L")
    else:
        img_gray = image

    binarized_image = img_gray.point(lambda x: 0 if x < threshold else 255, "1")

    return binarized_image
