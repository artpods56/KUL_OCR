from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette import status
from starlette.responses import StreamingResponse

from backend import dependencies
from . import schema, parsing, service

router = APIRouter()


@router.post("", response_model=schema.DocumentResponse)
def upload_document(
    file: Annotated[UploadFile, File()],
    storage: dependencies.FileStorageDep,
    uow: dependencies.UnitOfWorkDep,
    config: dependencies.AppConfigDep,
) -> schema.DocumentResponse:
    file_type = parsing.parse_file_type(file.content_type)

    service.validate_uploaded_file(
        file_stream=file.file,
        file_size=file.size or 0,
        file_type=file_type,
        max_bytes=config.max_upload_size_mb * 1024 * 1024,
    )

    document = service.prepare_document(
        file_name=file.filename or "unknown" + file_type.dot_extension,
        file_type=file_type,
        file_size=file.size or 0,
    )

    # Build storage paths using config
    staging_file_path = (
        Path(config.staging_prefix) / f"{document.id}{file_type.dot_extension}"
    )
    uploaded_file_path = (
        Path(config.documents_prefix) / f"{document.id}{file_type.dot_extension}"
    )

    return schema.DocumentResponse.from_dto(
        service.upload_document(
            file_stream=file.file,
            document=document,
            staging_file_path=staging_file_path,
            uploaded_file_path=uploaded_file_path,
            storage=storage,
            uow=uow,
        )
    )


@router.get("", response_model=schema.DocumentListResponse)
def list_documents(
    uow: dependencies.UnitOfWorkDep,
) -> schema.DocumentListResponse:
    return schema.DocumentListResponse.from_dto(service.get_documents(uow))


@router.get(
    "/{document_id}",
    response_model=schema.DocumentResponse,
)
def get_document(
    document_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schema.DocumentResponse:
    return schema.DocumentResponse.from_dto(service.get_document(str(document_id), uow))


@router.get(
    "/{document_id}/latest-result",
    response_model=schema.ResultResponse,
)
def get_latest_result(
    document_id: str,
    uow: dependencies.UnitOfWorkDep,
) -> schema.ResultResponse:
    result = service.get_latest_result_for_document(document_id, uow)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OCR result found for document {document_id}",
        )
    return schema.ResultResponse.from_dto(result)


@router.get("/{document_id}/download")
def download_document(
    document_id: UUID,
    storage: dependencies.FileStorageDep,
    uow: dependencies.UnitOfWorkDep,
):
    result = service.download_document(
        document_id=str(document_id), storage=storage, uow=uow
    )

    file_stream, content_type, filename = result

    return StreamingResponse(
        file_stream,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
