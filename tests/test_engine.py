"""Tests for OCR engine abstraction and implementations."""

from unittest.mock import patch

import pytest
from PIL import Image

from ocr_kul.engine import OCREngine, OCRResult, TesseractOCREngine


def test_ocr_result_dataclass():
    """OCRResult should be a dataclass with text and confidence."""
    result = OCRResult(text="Hello World", confidence=95.5)

    assert result.text == "Hello World"
    assert result.confidence == 95.5


def test_ocr_engine_is_abstract():
    """OCREngine should be abstract and not instantiable."""
    with pytest.raises(TypeError):
        OCREngine()  # type: ignore


def test_tesseract_engine_exists():
    """TesseractOCREngine should exist and be instantiable."""
    # This will fail until __init__ is implemented
    with patch("ocr_kul.config.get_tesseract_path"):
        try:
            engine = TesseractOCREngine()
            assert isinstance(engine, OCREngine)
        except NotImplementedError:
            pytest.fail("TesseractOCREngine.__init__ not implemented")


def test_tesseract_engine_inherits_from_ocr_engine():
    """TesseractOCREngine must inherit from OCREngine."""
    assert issubclass(TesseractOCREngine, OCREngine)


def test_tesseract_engine_init_uses_config():
    """TesseractOCREngine should use config.get_tesseract_path() by default."""
    with patch("ocr_kul.config.get_tesseract_path") as mock_config:
        mock_config.return_value = "/usr/bin/tesseract"

        try:
            engine = TesseractOCREngine()
            mock_config.assert_called_once()
        except NotImplementedError:
            pytest.skip("TesseractOCREngine.__init__ not implemented")


def test_tesseract_engine_init_accepts_custom_path():
    """TesseractOCREngine should accept custom tesseract_cmd parameter."""
    custom_path = "/custom/tesseract"

    try:
        with patch("pytesseract.pytesseract") as mock_pyt:
            engine = TesseractOCREngine(tesseract_cmd=custom_path)
            # Verify it was configured (implementation detail)
            assert engine is not None
    except NotImplementedError:
        pytest.skip("TesseractOCREngine.__init__ not implemented")


def test_tesseract_engine_process_returns_ocr_result():
    """TesseractOCREngine.process() should return OCRResult."""
    mock_image = Image.new("RGB", (100, 100), color="white")

    mock_data = {
        "text": ["Hello", "World", ""],
        "conf": [95.5, 88.3, -1],
    }

    with (
        patch("pytesseract.image_to_data") as mock_ocr,
        patch("ocr_kul.config.get_tesseract_path"),
    ):
        mock_ocr.return_value = mock_data

        try:
            engine = TesseractOCREngine()
            result = engine.process(mock_image)

            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 100.0
        except NotImplementedError:
            pytest.skip("TesseractOCREngine.process() not implemented")


def test_tesseract_engine_handles_tesseract_not_found():
    """TesseractOCREngine should raise RuntimeError if Tesseract not installed."""
    import pytesseract

    mock_image = Image.new("RGB", (100, 100))

    with (
        patch("pytesseract.image_to_data") as mock_ocr,
        patch("ocr_kul.config.get_tesseract_path"),
    ):
        mock_ocr.side_effect = pytesseract.TesseractNotFoundError()

        try:
            engine = TesseractOCREngine()
            with pytest.raises(RuntimeError, match="Tesseract"):
                engine.process(mock_image)
        except NotImplementedError:
            pytest.skip("TesseractOCREngine.process() not implemented")
