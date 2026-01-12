from typing import Annotated
from uuid import UUID
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, UploadFile, HTTPException, status
from fastapi import Query
from fastapi.responses import StreamingResponse
from kul_ocr.adapters.database import orm
from kul_ocr.domain import ports
from kul_ocr.entrypoints import dependencies, exception_handlers, schemas, tasks
from kul_ocr.domain import model, exceptions
from kul_ocr.service_layer import parsing, services, uow

_ = load_dotenv()

logger = logging.getLogger(__name__)

orm.start_mappers()

app = FastAPI()
router = APIRouter()


@router.post("/documents", response_model=schemas.DocumentResponse)
def upload_document(
    file: Annotated[UploadFile, File()],
    storage: Annotated[ports.FileStorage, Depends(dependencies.get_file_storage)],
    uow: Annotated[uow.AbstractUnitOfWork, Depends(dependencies.get_uow)],
) -> schemas.DocumentResponse:
    with uow:
        try:
            document = services.upload_document(
                file_stream=file.file,
                file_size=file.size or 0,
                file_type=parsing.parse_file_type(file.content_type),
                storage=storage,
                uow=uow,
            )
            uow.commit()
            return schemas.DocumentResponse.from_domain(document)
        except exceptions.FileUploadError:
            uow.rollback()
            raise


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    storage: ports.FileStorage = Depends(dependencies.get_file_storage),
    uow: uow.AbstractUnitOfWork = Depends(dependencies.get_uow),
):
    with uow:
        result = services.download_document(
            document_id=str(document_id), storage=storage, uow=uow
        )
        uow.commit()

        if result is None:
            raise HTTPException(status_code=404, detail="Document not found")

        file_stream, content_type, filename = result

        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@router.post(
    "/ocr/jobs",
    response_model=schemas.OCRJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ocr_job(
    request: schemas.CreateOCRJobRequest,
    uow: Annotated[uow.AbstractUnitOfWork, Depends(dependencies.get_uow)],
) -> schemas.OCRJobResponse:
    with uow:
        job = services.submit_ocr_job(str(request.document_id), uow)
        uow.commit()

        try:
            tasks.process_ocr_job_task.delay(str(job.id))
        except Exception as e:
            logger.error(
                f"Failed to trigger Celery task for job {job.id}: {e}",
                exc_info=True,
            )

        return schemas.OCRJobResponse.from_domain(job)


@router.get(
    "/documents/{document_id}",
    response_model=schemas.DocumentWithResultResponse,
)
def get_document(
    document_id: str,
    uow: Annotated[uow.AbstractUnitOfWork, Depends(dependencies.get_uow)],
) -> schemas.DocumentWithResultResponse:
    with uow:
        try:
            document, ocr_result = services.get_document_with_latest_result(
                document_id, uow
            )
            uow.commit()
            return schemas.DocumentWithResultResponse.from_domain(document, ocr_result)
        except ValueError as e:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found, error: {str(e)}"
            )


@router.get("/ocr/jobs", response_model=schemas.OCRJobListResponse)
def list_ocr_jobs(
    uow: Annotated[uow.AbstractUnitOfWork, Depends(dependencies.get_uow)],
    status: Annotated[
        str | None,
        Query(
            description="Filter by job status (pending, processing, completed, failed)"
        ),
    ] = None,
    document_id: Annotated[
        str | None, Query(description="Filter by document ID")
    ] = None,
) -> schemas.OCRJobListResponse:
    parsed_status = parse_job_status(status)

    with uow:
        jobs = services.get_ocr_jobs(
            uow=uow, status=parsed_status, document_id=document_id
        )
        uow.commit()
        return schemas.OCRJobListResponse.from_domain(list(jobs))


def parse_job_status(status: str | None) -> model.JobStatus | None:
    if status is None:
        return None
    try:
        return model.JobStatus(status)
    except ValueError:
        valid_options = [s.value for s in model.JobStatus]
        msg = f"Invalid status '{status}'. Valid options: {valid_options}"
        raise exceptions.InvalidJobStatusError(msg)


app.include_router(router)

exception_handlers.register_handlers(app)
