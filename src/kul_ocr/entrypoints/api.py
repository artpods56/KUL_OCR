from typing import Annotated
from uuid import UUID
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from kul_ocr.adapters.database import orm
from kul_ocr.domain import ports
from kul_ocr.entrypoints import dependencies, exception_handlers, schemas
from kul_ocr.service_layer import parsing, services, uow

_ = load_dotenv()

orm.start_mappers()

app = FastAPI()
router = APIRouter()


@router.post("/documents", response_model=schemas.DocumentResponse)
def upload_document(
    file: Annotated[UploadFile, File()],
    storage: Annotated[ports.FileStorage, Depends(dependencies.get_file_storage)],
    uow: Annotated[uow.AbstractUnitOfWork, Depends(dependencies.get_uow)],
) -> schemas.DocumentResponse:
    document = services.upload_document(
        file_stream=file.file,
        file_size=file.size or 0,
        file_type=parsing.parse_file_type(file.content_type),
        storage=storage,
        uow=uow,
    )
    return document


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    storage: Annotated[ports.FileStorage, Depends(dependencies.get_file_storage)],
    uow: Annotated[uow.AbstractUnitOfWork, Depends(dependencies.get_uow)],
):
    with uow:
        document = uow.documents.get(str(document_id))
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        storage_path_str = document.file_path
        content_type = document.file_type.value
        filename = f"{document.id}{document.file_type.dot_extension}"

    file_path = Path(storage_path_str)

    def file_iterator():
        with storage.load(file_path) as file_stream:
            yield from file_stream

    return StreamingResponse(
        file_iterator(),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app.include_router(router)

exception_handlers.register_handlers(app)
