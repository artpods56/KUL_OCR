from kul_ocr.domain import exceptions, model


def parse_file_type(content_type: str | None) -> model.FileType:
    if content_type is None:
        content_type = ""
    try:
        return model.FileType(content_type)
    except ValueError:
        raise exceptions.UnsupportedFileTypeError(
            f"Unsupported file type: {content_type}"
        )
