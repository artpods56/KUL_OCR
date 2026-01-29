import pytest

from core.domain import enums, exceptions
from core.service_layer import parsing


class TestParseFileType:
    @pytest.mark.parametrize(
        "content_type,expected_file_type",
        [
            ("application/pdf", enums.FileType.PDF),
            ("image/png", enums.FileType.PNG),
            ("image/jpeg", enums.FileType.JPEG),
            ("image/webp", enums.FileType.WEBP),
        ],
    )
    def test_parse_valid_content_types(
        self, content_type: str, expected_file_type: enums.FileType
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
