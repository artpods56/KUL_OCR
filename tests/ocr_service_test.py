import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
import tempfile
import json
import logging

logging.basicConfig(level=logging.WARNING)

from src.ocr.ocr_service import OcrService
from src.utils.file_manager import get_image_paths, save_json, save_text

@pytest.fixture
def temp_image_path(temp_dir) -> Path:
    img = Image.new('RGB', (20, 20), color='black')
    path = temp_dir / 'test_image.png'
    img.save(path, format='PNG')
    img.close()
    return path


@pytest.fixture
def temp_dir() -> Path:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)



@patch('pytesseract.get_tesseract_version', return_value='5.0.0')
@patch('src.ocr.ocr_service.TESSERACT_CMD', new='mocked/tesseract/path')
class TestOCRProcessor:

    def test_initialization_success_does_not_raise(self, mock_version):
        processor = OcrService()
        assert processor is not None
        assert processor.lang == 'eng'
        mock_version.assert_called_once()

    @patch('pytesseract.image_to_string', return_value='MOCKED TEXT')
    def test_process_image_contract_success(self, mock_to_string, mock_version, temp_image_path):
        processor = OcrService()
        result = processor.process_image(temp_image_path)

        assert isinstance(result, dict)
        assert result['status'] == 'success'
        assert result['text'] == 'MOCKED TEXT'
        assert result['error'] is None
        assert isinstance(result['processing_time'], float)
        mock_to_string.assert_called_once()

    @patch('pytesseract.image_to_string', side_effect=RuntimeError('Timeout'))
    def test_process_image_contract_timeout_error(self, mock_to_string, mock_version, temp_image_path):
        processor = OcrService()
        result = processor.process_image(temp_image_path)

        assert result['status'] == 'error'
        assert 'Timeout' in result['error']
        assert result['text'] == ''

    @patch('pytesseract.image_to_string', return_value='MOCKED TEXT')
    def test_process_batch_contract(self, mock_to_string, mock_version, temp_image_path):
        processor = OcrService()
        paths = [temp_image_path, temp_image_path]
        output = processor.process_batch(paths)

        assert 'metadata' in output
        assert 'results' in output
        assert output['metadata']['total_images'] == 2
        assert output['metadata']['successful'] == 2
        assert len(output['results']) == 2
        assert mock_to_string.call_count == 2



def test_get_image_paths_single_file_success(temp_image_path):
    paths = get_image_paths(str(temp_image_path))
    assert len(paths) == 1
    assert paths[0] == temp_image_path


def test_get_image_paths_directory_success(temp_dir):
    Image.new('RGB', (1, 1)).save(temp_dir / 'a.png', format='PNG')
    Image.new('RGB', (1, 1)).save(temp_dir / 'b.jpeg', format='JPEG')
    (temp_dir / 'c.txt').write_text('not an image')

    paths = get_image_paths(str(temp_dir))

    expected_paths = {temp_dir / 'a.png', temp_dir / 'b.jpeg'}

    assert len(paths) == 2
    assert set(paths) == expected_paths


def test_get_image_paths_nonexistent_raises_error():
    with pytest.raises(FileNotFoundError):
        get_image_paths('nonexistent_path.png')


def test_get_image_paths_unsupported_format_raises_error(temp_dir):
    unsupported_file = temp_dir / 'document.pdf'
    unsupported_file.touch()
    with pytest.raises(ValueError, match="Unsupported format"):
        get_image_paths(str(unsupported_file))


def test_save_json_creates_file_and_content(temp_dir):
    data = {'metadata': {'count': 1}, 'results': []}
    output_path = temp_dir / 'test.json'

    save_json(data, output_path)

    assert output_path.exists()
    with open(output_path, encoding='utf-8') as f:
        loaded = json.load(f)
    assert loaded['metadata']['count'] == 1


def test_save_text_creates_file_and_content(temp_dir):
    text = "Test content line 1\nTest content line 2"
    output_path = temp_dir / 'test.txt'

    save_text(text, output_path)

    assert output_path.exists()
    assert output_path.read_text(encoding='utf-8') == text