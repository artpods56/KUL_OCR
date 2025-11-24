import os
from dataclasses import dataclass
from typing import Self, cast, final, override

import pytesseract
from PIL import Image
from structlog import get_logger

from kul_ocr.domain import model, ports
from kul_ocr.utils.logger import Logger

logger: Logger = get_logger()


@dataclass
class TesseractEngineConfig:
    cmd: str

    @classmethod
    def from_env(cls) -> Self:
        tesseract_cmd = os.environ.get("TESSERACT_CMD", None)
        if tesseract_cmd is None:
            raise ValueError("TESSERACT_CMD variable must be set")

        return cls(
            cmd=tesseract_cmd,
        )


@final
class TesseractOCREngine(ports.OCREngine):
    SUPPORTED_FILE_TYPES = {
        model.FileType.PDF,
        model.FileType.PNG,
        model.FileType.JPG,
        model.FileType.JPEG,
    }

    def __init__(
        self, config: TesseractEngineConfig, document_loader: ports.DocumentLoader
    ):
        self.config = config
        self.document_loader = document_loader
        self._initialize_engine()
        self._validate_engine()

    @override
    def _initialize_engine(self) -> None:
        logger.info(f"Initialized `{self.engine_name}` OCR engine.")
        pytesseract.pytesseract.tesseract_cmd = self.config.cmd

    @override
    def _validate_engine(self) -> None:
        try:
            logger.info(f"Tesseract version: `{self.engine_version}`.")
        except Exception as e:
            raise RuntimeError(
                "Tesseract is not installed or not accessible.",
                f"TESSERACT_CMD: {self.config.cmd}",
                f"Error: {e}",
            )

    @override
    def _process_image(self, image: Image.Image) -> str:
        text = cast(str, pytesseract.image_to_string(image=image))

        return text

    @override
    def process_document(self, document: model.Document) -> model.OCRValueTypes:
        value_class = document.file_type.get_value_class()

        page_results: list[model.SinglePageOcrValue] = []

        for page_input in self.document_loader.load_pages(document):
            raw_text = self._process_image(page_input.image)

            page_results.append(
                model.SinglePageOcrValue(
                    page_number=page_input.page_number, content=raw_text
                )
            )

        if not page_results:
            raise ValueError(f"No content could be loaded from document {document.id}")

        if value_class is model.SimpleOCRValue:
            if len(page_results) > 1:
                pass
            return model.SimpleOCRValue(content=page_results[0].content)

        elif value_class is model.MultiPageOcrValue:
            return model.MultiPageOcrValue(content=page_results)

        elif value_class is model.SinglePageOcrValue:
            return page_results[0]

        else:
            raise NotImplementedError(f"Return type {value_class} not handled")

    @property
    @override
    def engine_name(self) -> str:
        return "tesseract"

    @property
    @override
    def engine_version(self) -> str:
        return str(pytesseract.get_tesseract_version())

    @override
    def supports_file_type(self, file_type: model.FileType) -> bool:
        return file_type in self.SUPPORTED_FILE_TYPES
