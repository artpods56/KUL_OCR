import io
from collections.abc import Iterator
from pathlib import Path
from typing import cast, override

import pymupdf  # PyMuPDF
from PIL import Image

from core.domain import enums, ports, model


class FileSystemDocumentLoader(ports.DocumentLoader):
    def __init__(self, storage: ports.FileStorage):
        self.storage = storage

    def _load_single_image(
            self, doc_input: model.DocumentInput
    ) -> Iterator[model.PageInput]:
        file_path = Path(doc_input.file_path)
        with self.storage.load(file_path) as file_stream:
            image_bytes = file_stream.read()
            with Image.open(io.BytesIO(image_bytes)) as img:
                loaded_img = img.convert("RGB")

        yield model.PageInput(
            image=loaded_img, page_number=1, original_document_id=doc_input.id
        )

    def _load_pdf_stream(
            self, doc_input: model.DocumentInput
    ) -> Iterator[model.PageInput]:
        """Yields pages one by one to keep RAM usage flat."""
        file_path = Path(doc_input.file_path)
        with self.storage.load(file_path) as file_stream:
            pdf_bytes = file_stream.read()

        pdf_document = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        try:
            for page_index in range(len(pdf_document)):
                page = pdf_document[page_index]

                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2),
                                      alpha=False)  # pyright: ignore[reportAttributeAccessIssue]

                w = cast(int, pix.width)
                h = cast(int, pix.height)

                img = Image.frombytes("RGB", (w, h), pix.samples)

                yield model.PageInput(
                    image=img,
                    page_number=page_index + 1,
                    original_document_id=doc_input.id,
                )

                del img
                del pix
        finally:
            pdf_document.close()

    @override
    def load_pages(self, doc_input: model.DocumentInput) -> Iterator[model.PageInput]:
        if doc_input.file_type == enums.FileType.PDF:
            yield from self._load_pdf_stream(doc_input)
        elif doc_input.file_type.is_image:
            yield from self._load_single_image(doc_input)
        else:
            raise ValueError(f"Unsupported file type: {doc_input.file_type}")
