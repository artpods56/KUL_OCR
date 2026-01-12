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
    """Configuration object for the Tesseract OCR engine.

    This dataclass encapsulates configuration requires to initialize
    the Tesseract OCR backend, primarily the path to the Tesseract
    executable binary.

    Attributes:
        cmd: Absolute path to the Tesseract executable.
    """

    cmd: str

    @classmethod
    def from_env(cls) -> Self:
        """Create TesseractEngineConfig from enviroment variables.

        Reads the ''TESSERACT_CMD'' enviroment variable, whitch must point
        to the Tesseract executable installed on the system.

        Returns:
            A full initialized TesseractEngineConfig instance.

        Raises:
            ValueError: If the ''TESSERACT_CMD''  enviroment variables in not set
        """
        tesseract_cmd = os.environ.get("TESSERACT_CMD", None)
        if tesseract_cmd is None:
            raise ValueError("TESSERACT_CMD variable must be set")

        return cls(
            cmd=tesseract_cmd,
        )


@final
class TesseractOCREngine(ports.OCREngine):
    """Tesseract-based OCR engine implementation.

    This adapter connects the application to the external Tesseract OCR
    engine via the ''pytesseract'' library. It implements the
    :class:'OCREngine' abstract interface defined in ''ports.py''.

    The engine supports OCR for both single-image documents and multi-page PDFs.
    PDFs are processed page-by=page to avoid loading the entire document into memory at once.

    External dependencies:
        -Tesseract OCR
        -pytesseract Python bindings
        -PIL/Pillow for image handling

    Performance notes:
        -OCR is CPU-bound and processing time scales lineary with the number of pages.
        -Accuracy depends heavily on image quality and Tesseract language configuration.
    """

    SUPPORTED_FILE_TYPES = {
        model.FileType.PDF,
        model.FileType.PNG,
        model.FileType.JPG,
        model.FileType.JPEG,
    }

    def __init__(
        self, config: TesseractEngineConfig, document_loader: ports.DocumentLoader
    ):
        """Initialize the Tesseract OCR engine adapter.

        During initialization, the Tesseract executable path is configured
        and a validation step is performed to ensure the engine is usable.

        Args:
            config: Configuration containing the Tesseract executable path.
            document_loader: Component responsible for loading documents as a stream of images.

        Raises:
            RuntimeError: If the Tesseract engine cannot be initialized or validated.
        """
        self.config = config
        self.document_loader = document_loader
        self._initialize_engine()
        self._validate_engine()

    @override
    def _initialize_engine(self) -> None:
        """Initialize the Tesseract OCR engine.

        Configures ''pytesseract'' to use the Tesseract executable specified
        in the engine configuration.

        This method fulfills the initialization contract defined by :class:'OCREngine'.
        It must be called begore any OCR operations are performed.

        Side effects:
            -Sets a global pytesseract configuration value.
        """
        logger.info(f"Initialized `{self.engine_name}` OCR engine.")
        pytesseract.pytesseract.tesseract_cmd = self.config.cmd

    @override
    def _validate_engine(self) -> None:
        """Validate that the Tesseract engine is available and functional.

        Attempts to query the Tesseract version to verify that the binary
        is correctly installed and accessible.

        Raises:
            RuntimeError: If the Tesseract binary is not installed,
                not executable, or cannot be accused using the configured
                command path.
        """
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
        """Extract text from a single image using Tesseract OCR.

        This method performs the core OCR operation. It takes a PIL Image,
        passes it to via ''pytesseract'', and returns the extracted text.

        Assumptions:
            -The image is already loaded and in a format compatible
            with Tesseract.
            -No additional preprocessing is performed at this stage.

        Accuracy notes:
            OCR accuracy depends om image quality, resulotion,
            and language configuration of the Tesserat engine.

        Args:
            image: PIL Image object to process.

        Returns:
            Extracted text as a string. Returns an empty string if
            no text is detected.
        """
        text = cast(str, pytesseract.image_to_string(image=image))

        return text

    @override
    def process_document(self, document: model.Document) -> model.OCRValueTypes:
        """Process a document and extract text using Tesseract OCR.

        This method implements the core contract of the :class:'OCREngine' interface.
        The document is loaded as a sequence if images using the provided
        ''DocumentLoader'' and OCR is performed page-by=page.

        he return type depends in the document's file type:
        -Images returns :class:'SimpleOCRValue'
        -PDFs return :class:'MultiPageValue'

        Performance considerations:
            -Pages are processed sequentially to limit memory usage.
            -Processing time increases linearly with page count.

        Args:
            document: The document to process.

        Returns:
            OCR results structured according to the document type.

        Raises:
            ValueError: If no pages could be loaded from the document.
            RuntimeError: If OCR processing fails due to engine errors.
            NotImplementedError: If hr resolved OCR returns type is not supported.
        """
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
        """Return the identifier name of this OCR engine.

        Returns:
            Always returns ''"tesseract"'' for this implementation.
        """
        return "tesseract"

    @property
    @override
    def engine_version(self) -> str:
        """Return the version of the Tesseract engine in use.

        The version is obtained by querying the installed Tesseract
        binary via ''pytesseract''.

        Returns:
            Version string
        """
        return str(pytesseract.get_tesseract_version())

    @override
    def supports_file_type(self, file_type: model.FileType) -> bool:
        """Check whether a file type is supported by this OCR engine.

        This method fulfills the :class:'OCREngine' contract and is used to
        determine whether the engine can process a given document.

        Args:
            file_type: File type to check.

        Returns:
            ''True'' if the file type is supported, ''False'' otherwise.
        """
        return file_type in self.SUPPORTED_FILE_TYPES
