from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, UploadFile

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


app.include_router(router)

exception_handlers.register_handlers(app)
