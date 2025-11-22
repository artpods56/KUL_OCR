"""Image preprocessing functions for OCR quality improvement.

This module provides image enhancement functions that work on PIL Images.
All functions take a PIL Image and return a modified PIL Image.
"""
#sorry for stupid errors messages, but...I'm your father
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
    image=image.convert('L')
    image=ImageEnhance.Contrast(image).enhance(1.5)
    image=ImageEnhance.Sharpness(image).enhance(2.0)
    image=image.filter(ImageFilter.MedianFilter(size=3))
    return image


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
    if scale_factor<=0:
        raise ValueError(f"scale_factor is not big enough for this ride, he is only {scale_factor}")
    width,height=image.size
    new_size=(width * scale_factor, height * scale_factor)
    resized_image=image.resize(new_size,resample=Image.Resampling.LANCZOS)
    return resized_image


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
    if not (threshold>=0 and threshold<=255):
        raise ValueError(f"We are very sorry, but your threshold do not meet our expectation...so we kill it, it must be between 0 and 255, but you gave us {threshold}...how dere you")
    image=image.convert('L')
    image=image.point(lambda x: 0 if x < threshold else 255, '1')
    return image