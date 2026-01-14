from unittest.mock import Mock
from PIL import Image
import pytest

from kul_ocr.domain import model, ports, structs
from kul_ocr.service_layer import services


@pytest.fixture
def mock_ocr_engine():
    return Mock(spec=ports.OCREngine)


@pytest.fixture
def mock_document_loader():
    return Mock(spec=ports.DocumentLoader)


@pytest.fixture
def sample_image():
    return Image.new("RGB", (10, 10), color="white")


def test_process_document_orchestration(
    mock_ocr_engine, mock_document_loader, sample_image
):
    # Arrange
    doc_input = structs.DocumentInput(
        id="doc1",
        file_path="doc1.png",
        file_type=model.FileType.PNG,
    )

    mock_document_loader.load_pages.return_value = [
        structs.PageInput(
            image=sample_image, page_number=1, original_document_id="doc1"
        )
    ]
    mock_ocr_engine.process_image.return_value = "extracted text"

    # Act
    result = services.process_document(
        doc_input=doc_input,
        ocr_engine=mock_ocr_engine,
        document_loader=mock_document_loader,
    )

    # Assert
    assert isinstance(result, model.Result)
    assert result.job_id == ""
    assert len(result.content) == 1
    assert result.content[0].result.full_text == "extracted text"
    mock_document_loader.load_pages.assert_called_once_with(doc_input)
    mock_ocr_engine.process_image.assert_called_once_with(sample_image)


def test_process_document_multi_page_orchestration(
    mock_ocr_engine, mock_document_loader, sample_image
):
    # Arrange
    doc_input = structs.DocumentInput(
        id="doc2",
        file_path="doc2.pdf",
        file_type=model.FileType.PDF,
    )

    mock_document_loader.load_pages.return_value = [
        structs.PageInput(
            image=sample_image, page_number=1, original_document_id="doc2"
        ),
        structs.PageInput(
            image=sample_image, page_number=2, original_document_id="doc2"
        ),
    ]
    mock_ocr_engine.process_image.side_effect = ["text 1", "text 2"]

    # Act
    result = services.process_document(
        doc_input=doc_input,
        ocr_engine=mock_ocr_engine,
        document_loader=mock_document_loader,
    )

    # Assert
    assert isinstance(result, model.Result)
    assert len(result.content) == 2
    assert result.content[0].result.full_text == "text 1"
    assert result.content[1].result.full_text == "text 2"
    assert mock_ocr_engine.process_image.call_count == 2


def test_process_document_raises_if_no_pages(mock_ocr_engine, mock_document_loader):
    # Arrange
    doc_input = structs.DocumentInput(
        id="doc3",
        file_path="doc3.png",
        file_type=model.FileType.PNG,
    )
    mock_document_loader.load_pages.return_value = []

    # Act & Assert
    with pytest.raises(ValueError, match="No content could be loaded"):
        services.process_document(
            doc_input=doc_input,
            ocr_engine=mock_ocr_engine,
            document_loader=mock_document_loader,
        )
