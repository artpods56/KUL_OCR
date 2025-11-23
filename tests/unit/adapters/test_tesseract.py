from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from ocr_kul.adapters.ocr.tesseract import TesseractEngineConfig, TesseractOCREngine
from ocr_kul.domain import model, ports, structs
from tests import factories


@pytest.fixture
def config() -> TesseractEngineConfig:
    return TesseractEngineConfig(cmd="/usr/bin/tesseract")


@pytest.fixture
def mock_loader() -> Mock:
    """Create a mock document loader."""
    return Mock(spec=ports.DocumentLoader)


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
    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_initialization_sets_tesseract_cmd(
        self, mock_pytesseract, config: TesseractEngineConfig, mock_loader: Mock
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"

        TesseractOCREngine(config, mock_loader)

        assert mock_pytesseract.pytesseract.tesseract_cmd == config.cmd

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_validate_engine_raises_on_invalid_tesseract(
        self, mock_pytesseract, config: TesseractEngineConfig, mock_loader: Mock
    ):
        mock_pytesseract.get_tesseract_version.side_effect = Exception(
            "Tesseract not found"
        )

        with pytest.raises(
            RuntimeError, match="Tesseract is not installed or not accessible"
        ):
            TesseractOCREngine(config, mock_loader)

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_engine_name_property(
        self, mock_pytesseract, config: TesseractEngineConfig, mock_loader: Mock
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"

        engine = TesseractOCREngine(config, mock_loader)

        assert engine.engine_name == "tesseract"

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_engine_version_property(
        self, mock_pytesseract, config: TesseractEngineConfig, mock_loader: Mock
    ):
        expected_version = "5.3.0"
        mock_pytesseract.get_tesseract_version.return_value = expected_version

        engine = TesseractOCREngine(config, mock_loader)

        assert engine.engine_version == expected_version

    @pytest.mark.parametrize(
        "file_type,expected_support",
        [
            (model.FileType.PDF, True),
            (model.FileType.PNG, True),
            (model.FileType.JPG, True),
            (model.FileType.JPEG, True),
            (model.FileType.WEBP, False),
        ],
    )
    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_supports_file_type(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        mock_loader: Mock,
        file_type: model.FileType,
        expected_support: bool,
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        engine = TesseractOCREngine(config, mock_loader)

        assert engine.supports_file_type(file_type) is expected_support

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_process_image_calls_pytesseract(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        mock_loader: Mock,
        sample_image: Image.Image,
    ):
        expected_text = "Extracted text"
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.image_to_string.return_value = expected_text

        engine = TesseractOCREngine(config, mock_loader)
        result = engine._process_image(sample_image)

        mock_pytesseract.image_to_string.assert_called_once_with(image=sample_image)
        assert result == expected_text

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_process_document_simple_image(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        mock_loader: Mock,
        sample_image: Image.Image,
        tmp_path: Path,
    ):
        expected_text = "Test text from image"
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.image_to_string.return_value = expected_text

        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PNG
        )

        mock_loader.load_pages.return_value = [
            structs.PageInput(
                image=sample_image, page_number=1, original_document_id=document.id
            )
        ]

        engine = TesseractOCREngine(config, mock_loader)
        result = engine.process_document(document)

        assert isinstance(result, model.SimpleOCRValue)
        assert result.content == expected_text

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_process_document_pdf(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        mock_loader: Mock,
        sample_image: Image.Image,
        tmp_path: Path,
    ):
        page_texts = ["Page 1 text", "Page 2 text", "Page 3 text"]
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.image_to_string.side_effect = page_texts

        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PDF
        )

        mock_loader.load_pages.return_value = [
            structs.PageInput(
                image=sample_image, page_number=i + 1, original_document_id=document.id
            )
            for i in range(len(page_texts))
        ]

        engine = TesseractOCREngine(config, mock_loader)
        result = engine.process_document(document)

        assert isinstance(result, model.MultiPageOcrValue)
        assert len(result.content) == len(page_texts)
        for i, expected_text in enumerate(page_texts):
            assert result.content[i].page_number == i + 1
            assert result.content[i].content == expected_text

    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_process_document_raises_on_empty_content(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        mock_loader: Mock,
        tmp_path: Path,
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"

        document = factories.generate_document(
            dir_path=tmp_path, file_type=model.FileType.PDF
        )
        mock_loader.load_pages.return_value = []

        engine = TesseractOCREngine(config, mock_loader)

        with pytest.raises(
            ValueError, match="No content could be loaded from document"
        ):
            engine.process_document(document)

    @pytest.mark.parametrize(
        "file_type,expected_value_class",
        [
            (model.FileType.PNG, model.SimpleOCRValue),
            (model.FileType.PDF, model.MultiPageOcrValue),
        ],
    )
    @patch("ocr_kul.adapters.ocr.tesseract.pytesseract")
    def test_process_document_uses_correct_value_class(
        self,
        mock_pytesseract,
        config: TesseractEngineConfig,
        mock_loader: Mock,
        sample_image: Image.Image,
        tmp_path: Path,
        file_type: model.FileType,
        expected_value_class: type[model.OCRValueTypes],
    ):
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.image_to_string.return_value = "Test"

        document = factories.generate_document(dir_path=tmp_path, file_type=file_type)
        mock_loader.load_pages.return_value = [
            structs.PageInput(
                image=sample_image, page_number=1, original_document_id=document.id
            )
        ]

        engine = TesseractOCREngine(config, mock_loader)
        result = engine.process_document(document)

        assert isinstance(result, expected_value_class)
