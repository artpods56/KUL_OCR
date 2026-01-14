from unittest.mock import patch

import pytest
from PIL import Image

from kul_ocr.adapters.ocr.tesseract import TesseractEngineConfig, TesseractOCREngine
from kul_ocr.domain import model


@pytest.fixture
def config() -> TesseractEngineConfig:
    return TesseractEngineConfig(cmd="/usr/bin/tesseract")


@pytest.fixture
def sample_image() -> Image.Image:
    """Create a simple test image."""
    return Image.new("RGB", (100, 100), color="white")


class TestTesseractEngineConfig:
    def test_from_env_with_tesseract_cmd_set(self, monkeypatch):
        monkeypatch.setenv("TESSERACT_CMD", "/usr/bin/tesseract")

        config = TesseractEngineConfig.from_env()

        assert config.cmd == "/usr/bin/tesseract"

    def test_from_env_without_tesseract_cmd_raises_error(self, monkeypatch):
        monkeypatch.delenv("TESSERACT_CMD", raising=False)

        with pytest.raises(ValueError, match="TESSERACT_CMD variable must be set"):
            TesseractEngineConfig.from_env()


class TestTesseractOCREngine:
    @patch("kul_ocr.adapters.ocr.tesseract.pytesseract")
    def test_initialization_sets_tesseract_cmd(
        self, mock_pytesseract, config: TesseractEngineConfig
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"

        TesseractOCREngine(config)

        assert mock_pytesseract.pytesseract.tesseract_cmd == config.cmd

    @patch("kul_ocr.adapters.ocr.tesseract.pytesseract")
    def test_validate_engine_raises_on_invalid_tesseract(
        self, mock_pytesseract, config: TesseractEngineConfig
    ):
        mock_pytesseract.get_tesseract_version.side_effect = Exception(
            "Tesseract not found"
        )

        with pytest.raises(
            RuntimeError, match="Tesseract is not installed or not accessible"
        ):
            TesseractOCREngine(config)

    @patch("kul_ocr.adapters.ocr.tesseract.pytesseract")
    def test_engine_name_property(
        self, mock_pytesseract, config: TesseractEngineConfig
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"

        engine = TesseractOCREngine(config)

        assert engine.engine_name == "tesseract"

    @patch("kul_ocr.adapters.ocr.tesseract.pytesseract")
    def test_engine_version_property(
        self, mock_pytesseract, config: TesseractEngineConfig
    ):
        expected_version = "5.3.0"
        mock_pytesseract.get_tesseract_version.return_value = expected_version

        engine = TesseractOCREngine(config)

        assert engine.engine_version == expected_version

    @pytest.mark.parametrize(
        "file_type,expected_support",
        [
            (model.FileType.PDF, False),
            (model.FileType.PNG, True),
            (model.FileType.JPG, True),
            (model.FileType.JPEG, True),
            (model.FileType.WEBP, False),
        ],
    )
    @patch("kul_ocr.adapters.ocr.tesseract.pytesseract")
    def test_supports_file_type(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        file_type: model.FileType,
        expected_support: bool,
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        engine = TesseractOCREngine(config)

        assert engine.supports_file_type(file_type) is expected_support

    @patch("kul_ocr.adapters.ocr.tesseract.pytesseract")
    def test_process_image_calls_pytesseract(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        sample_image: Image.Image,
    ):
        expected_text = "Extracted text"
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.image_to_string.return_value = expected_text

        engine = TesseractOCREngine(config)
        result = engine.process_image(sample_image)

        mock_pytesseract.image_to_string.assert_called_once_with(image=sample_image)
        assert result == expected_text
