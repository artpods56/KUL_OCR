from typing import Annotated
from uuid import UUID
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, UploadFile, HTTPException, status
from fastapi import Query
from fastapi.responses import StreamingResponse
from kul_ocr.adapters.database import orm
from kul_ocr.entrypoints import dependencies, exception_handlers, schemas, tasks
from kul_ocr.entrypoints.dependencies import UnitOfWorkDep
from kul_ocr.service_layer import parsing, services

_ = load_dotenv()

logger = logging.getLogger(__name__)

orm.start_mappers()

app = FastAPI()
router = APIRouter()


"""
--- Documents API ---
endpoints:
[x] - POST /documents: Upload a document
[x] - GET /documents/{document_id}: Get a document by ID
[x] - GET /documents/{document_id}/latest-result: Get the latest OCR result for a document
[x] - GET /documents/{document_id}/download: Download a document
"""


@router.post("/documents", response_model=schemas.DocumentResponse)
def upload_document(
    file: Annotated[UploadFile, File()],
    storage: dependencies.FileStorageDep,
    uow: UnitOfWorkDep,
) -> schemas.DocumentResponse:
    return services.upload_document(
        file_stream=file.file,
        file_size=file.size or 0,
        file_type=parsing.parse_file_type(file.content_type),
        storage=storage,
        uow=uow,
    )


@router.get(
    "/documents/{document_id}",
    response_model=schemas.DocumentResponse,
)
def get_document(
    document_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schemas.DocumentResponse:
    return services.get_document(document_id, uow)


@router.get(
    "/documents/{document_id}/latest-result",
    response_model=schemas.ResultResponse,
)
def get_latest_result(
    document_id: str,
    uow: dependencies.UnitOfWorkDep,
) -> schemas.ResultResponse:
    result = services.get_latest_result_for_document(document_id, uow)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OCR result found for document {document_id}",
        )
    return result


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    storage: dependencies.FileStorageDep,
    uow: UnitOfWorkDep,
):
    result = services.download_document(
        document_id=str(document_id), storage=storage, uow=uow
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_stream, content_type, filename = result

    return StreamingResponse(
        file_stream,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


"""
--- OCR Jobs API ---
endpoints:
[x] - POST /ocr/jobs: Submit a new OCR job
[ ] - POST /ocr/jobs/{job_id}/start: Start execution of a pending OCR job
[ ] - POST /ocr/jobs/{job_id}/cancel: Cancel pending or running OCR job (gracefully if possible)
[ ] - POST /ocr/jobs/{job_id}/retry: Retry a failed OCR job
[ ] - DELETE /ocr/jobs/{job_id}: Delete OCR Job in terminal state
[x] - GET /ocr/jobs: List OCR jobs (supports filtering by status, pagination) [TODO] pagination
[ ] - GET /ocr/jobs/{job_id}: Get an OCR job by ID
"""


@router.post(
    "/ocr/jobs",
    response_model=schemas.JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ocr_job(
    request: schemas.CreateJobRequest,
    uow: UnitOfWorkDep,
) -> schemas.JobResponse:
    return services.submit_ocr_job(str(request.document_id), uow)


@router.post("/ocr/jobs/{job_id}/start")
def start_ocr_job(
    job_id: UUID,
    uow: UnitOfWorkDep,
) -> schemas.JobResponse:
    try:
        response = services.start_ocr_job_processing(job_id, uow=uow)
        tasks.process_ocr_job_task.delay(str(job_id))
        return response
    except Exception as e:
        job = services.fail_ocr_job(job_id, str(e), uow=uow)
        return schemas.JobResponse.from_domain(job)


@router.get("/ocr/jobs", response_model=schemas.JobListResponse)
def list_ocr_jobs(
    uow: UnitOfWorkDep,
    status: Annotated[
        str | None,
        Query(
            description="Filter by job status (pending, processing, completed, failed)"
        ),
    ] = None,
    document_id: Annotated[
        UUID | None, Query(description="Filter by document ID")
    ] = None,
) -> schemas.JobListResponse:
    return services.get_ocr_jobs(uow=uow, status=status, document_id=document_id)


app.include_router(router)

exception_handlers.register_handlers(app)
