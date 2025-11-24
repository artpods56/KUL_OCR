from typing import Iterator, cast, override

import pymupdf  # PyMuPDF
from PIL import Image

from kul_ocr.domain import model, ports, structs


class FileSystemDocumentLoader(ports.DocumentLoader):
    def _load_single_image(
        self, document: model.Document
    ) -> Iterator[structs.PageInput]:
        with Image.open(document.file_path) as img:
            loaded_img = img.convert("RGB")

        yield structs.PageInput(
            image=loaded_img, page_number=1, original_document_id=document.id
        )

    def _load_pdf_stream(self, document: model.Document) -> Iterator[structs.PageInput]:
        """Yields pages one by one to keep RAM usage flat."""
        pdf_document = pymupdf.open(document.file_path)

        try:
            for page_index in range(len(pdf_document)):
                page = pdf_document[page_index]

                pix = page.get_pixmap(alpha=False)

                w = cast(int, pix.width)
                h = cast(int, pix.height)

                img = Image.frombytes("RGB", (w, h), pix.samples)

                yield structs.PageInput(
                    image=img,
                    page_number=page_index + 1,
                    original_document_id=document.id,
                )

                del img
                del pix
        finally:
            pdf_document.close()

    @override
    def load_pages(self, document: model.Document) -> Iterator[structs.PageInput]:
        if document.is_pdf():
            yield from self._load_pdf_stream(document)
        elif document.is_image():
            yield from self._load_single_image(document)
        else:
            raise ValueError(f"Unsupported file type: {document.file_type}")
