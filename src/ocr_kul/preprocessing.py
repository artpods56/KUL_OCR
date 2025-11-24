from typing import Union, Any

from PIL import Image, ImageEnhance, ImageFilter

RESAMPLE_LANCZOS: Any

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_LANCZOS = getattr(Image, "LANCZOS")


def enhance_image(image: Image.Image) -> Image.Image:
    CONTRAST_FACTOR = 1.5
    SHARPNESS_FACTOR = 2.0
    MEDIAN_FILTER_SIZE = 3

    enhanced_img = image.convert("L")

    contrast_enhancer = ImageEnhance.Contrast(enhanced_img)
    enhanced_img = contrast_enhancer.enhance(CONTRAST_FACTOR)

    sharpness_enhancer = ImageEnhance.Sharpness(enhanced_img)
    enhanced_img = sharpness_enhancer.enhance(SHARPNESS_FACTOR)

    enhanced_img = enhanced_img.filter(
        ImageFilter.MedianFilter(size=MEDIAN_FILTER_SIZE)
    )

    return enhanced_img


def resize_image(
    image: Image.Image, scale_factor: Union[int, float] = 2.0
) -> Image.Image:
    if scale_factor <= 0:
        raise ValueError(f"Scale factor must be positive, got {scale_factor}")

    width, height = image.size
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    resized_image = image.resize((new_width, new_height), resample=RESAMPLE_LANCZOS)

    return resized_image


def binarize_image(image: Image.Image, threshold: int = 128) -> Image.Image:
    if not 0 <= threshold <= 255:
        raise ValueError(
            f"Threshold must be between 0 and 255 (inclusive), got {threshold}"
        )

    img_gray = image if image.mode == "L" else image.convert("L")

    binarized_image = img_gray.point(lambda x: 0 if x < threshold else 255, "1")

    return binarized_image
