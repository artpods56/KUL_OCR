import pytest

from ocr_kul.domain import exceptions, model
from ocr_kul.service_layer import parsing


class TestParseFileType:
    @pytest.mark.parametrize(
        "content_type,expected_file_type",
        [
            ("application/pdf", model.FileType.PDF),
            ("image/png", model.FileType.PNG),
            ("image/jpeg", model.FileType.JPEG),
            ("image/webp", model.FileType.WEBP),
        ],
    )
    def test_parse_valid_content_types(
        self, content_type: str, expected_file_type: model.FileType
    ):
        result = parsing.parse_file_type(content_type)
        assert result == expected_file_type

    @pytest.mark.parametrize(
        "invalid_content_type",
        ["invalid/type", None, ""],
    )
    def test_parse_invalid_content_type_raises_exception(
        self, invalid_content_type: str | None
    ):
        with pytest.raises(exceptions.UnsupportedFileTypeError):
            _ = parsing.parse_file_type(invalid_content_type)
