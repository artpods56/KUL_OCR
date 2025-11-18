"""Tests for image preprocessing functionality."""

import pytest
from PIL import Image

from ocr_kul.preprocessing import binarize_image, enhance_image, resize_image


def test_enhance_image_returns_image():
    """enhance_image must return a PIL Image."""
    test_img = Image.new("RGB", (100, 100), color="red")

    try:
        result = enhance_image(test_img)
        assert isinstance(result, Image.Image)
    except NotImplementedError:
        pytest.skip("enhance_image() not implemented")


def test_enhance_image_converts_to_grayscale():
    """enhance_image must convert image to grayscale."""
    test_img = Image.new("RGB", (100, 100), color="red")

    try:
        result = enhance_image(test_img)
        assert result.mode == "L", "Image must be grayscale (mode 'L')"
    except NotImplementedError:
        pytest.skip("enhance_image() not implemented")


def test_enhance_image_preserves_dimensions():
    """enhance_image should preserve image dimensions."""
    test_img = Image.new("RGB", (200, 150), color="blue")

    try:
        result = enhance_image(test_img)
        assert result.size == (200, 150), "Dimensions should be preserved"
    except NotImplementedError:
        pytest.skip("enhance_image() not implemented")


def test_resize_image_validates_scale_factor():
    """resize_image must raise ValueError for invalid scale_factor."""
    test_img = Image.new("RGB", (100, 100))

    with pytest.raises(ValueError):
        resize_image(test_img, scale_factor=0.0)

    with pytest.raises(ValueError):
        resize_image(test_img, scale_factor=-1.0)


def test_resize_image_returns_correct_size():
    """resize_image must resize image by correct factor."""
    test_img = Image.new("RGB", (100, 100))

    try:
        result = resize_image(test_img, scale_factor=2.0)
        assert result.size == (200, 200), "Image must be 2x larger"
    except NotImplementedError:
        pytest.skip("resize_image() not implemented")


def test_resize_image_returns_image():
    """resize_image must return a PIL Image."""
    test_img = Image.new("RGB", (100, 100))

    try:
        result = resize_image(test_img, scale_factor=1.5)
        assert isinstance(result, Image.Image)
    except NotImplementedError:
        pytest.skip("resize_image() not implemented")


def test_binarize_image_validates_threshold():
    """binarize_image must validate threshold is in range 0-255."""
    test_img = Image.new("RGB", (100, 100))

    with pytest.raises(ValueError):
        binarize_image(test_img, threshold=256)

    with pytest.raises(ValueError):
        binarize_image(test_img, threshold=-1)


def test_binarize_image_creates_binary_output():
    """binarize_image must create pure black and white image."""
    test_img = Image.new("L", (100, 100), color=150)  # Gray image

    try:
        result = binarize_image(test_img, threshold=128)

        # Check mode is binary
        assert result.mode == "1", "Binary image must have mode '1'"

        # All pixels should be either 0 or 255 when converted back
        pixels = list(result.convert("L").getdata())
        assert all(p in [0, 255] for p in pixels), (
            "Binary image must only contain 0 (black) or 255 (white)"
        )
    except NotImplementedError:
        pytest.skip("binarize_image() not implemented")


def test_binarize_image_returns_image():
    """binarize_image must return a PIL Image."""
    test_img = Image.new("L", (100, 100), color=128)

    try:
        result = binarize_image(test_img)
        assert isinstance(result, Image.Image)
    except NotImplementedError:
        pytest.skip("binarize_image() not implemented")
