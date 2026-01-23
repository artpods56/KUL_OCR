from typing import Annotated
from uuid import UUID
import logging

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, UploadFile, HTTPException, status
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

import kul_ocr.adapters.database.repository
import kul_ocr.service_layer.services.documents
import kul_ocr.service_layer.services.jobs
import kul_ocr.service_layer.services.results
from kul_ocr.adapters.database import orm
from kul_ocr.entrypoints import dependencies, exception_handlers, schemas
from kul_ocr.entrypoints.dependencies import UnitOfWorkDep
from kul_ocr.service_layer import parsing

_ = load_dotenv()

logger = logging.getLogger(__name__)

orm.start_mappers()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()


"""
--- Documents API ---
endpoints:
[x] - POST /documents: Upload a document
[x] - GET /documents: List all documents
[x] - GET /documents/{document_id}: Get a document by ID
[x] - GET /documents/{document_id}/latest-result: Get the latest OCR result for a document
[x] - GET /documents/{document_id}/download: Download a document
"""


@router.post("/documents", response_model=schemas.DocumentResponse)
def upload_document(
    file: Annotated[UploadFile, File()],
    storage: dependencies.FileStorageDep,
    uow: UnitOfWorkDep,
    config: dependencies.AppConfigDep,
) -> schemas.DocumentResponse:
    file_type = parsing.parse_file_type(file.content_type)

    return schemas.DocumentResponse.from_dto(
        kul_ocr.service_layer.services.documents.upload_document(
            file_stream=file.file,
            file_size=file.size or 0,
            file_type=file_type,
            storage=storage,
            uow=uow,
            original_filename=file.filename,
            max_bytes=config.max_upload_size_mb * 1024 * 1024,
        )
    )


@router.get("/documents", response_model=schemas.DocumentListResponse)
def list_documents(
    uow: UnitOfWorkDep,
) -> schemas.DocumentListResponse:
    return schemas.DocumentListResponse.from_dto(
        kul_ocr.service_layer.services.documents.get_documents(uow)
    )


@router.get(
    "/documents/{document_id}",
    response_model=schemas.DocumentResponse,
)
def get_document(
    document_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schemas.DocumentResponse:
    return schemas.DocumentResponse.from_dto(
        kul_ocr.service_layer.services.documents.get_document(str(document_id), uow)
    )


@router.get(
    "/documents/{document_id}/latest-result",
    response_model=schemas.ResultResponse,
)
def get_latest_result(
    document_id: str,
    uow: dependencies.UnitOfWorkDep,
) -> schemas.ResultResponse:
    result = kul_ocr.service_layer.services.results.get_latest_result_for_document(
        document_id, uow
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OCR result found for document {document_id}",
        )
    return schemas.ResultResponse.from_dto(result)


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    storage: dependencies.FileStorageDep,
    uow: UnitOfWorkDep,
):
    result = kul_ocr.service_layer.services.results.download_document(
        document_id=str(document_id), storage=storage, uow=uow
    )

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
[x] - POST /ocr/jobs/{job_id}/retry: Retry a failed OCR job
[x] - DELETE /ocr/jobs/{job_id}: Delete OCR Job in terminal state
[x] - GET /ocr/jobs: List OCR jobs (supports filtering by status, pagination) [TODO] pagination
[x] - GET /ocr/jobs/{job_id}: Get an OCR job by ID
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
    return schemas.JobResponse.from_dto(
        kul_ocr.service_layer.services.jobs.submit_ocr_job(
            str(request.document_id), uow
        )
    )


@router.post("/ocr/jobs/{job_id}/start")
def start_ocr_job(
    job_id: UUID,
    uow: UnitOfWorkDep,
) -> schemas.JobResponse:
    """Start processing an OCR job.

    Marks the job as PROCESSING and creates an outbox entry for reliable
    task scheduling. The outbox relay will pick up the entry and schedule
    the Celery task.
    """
    try:
        job_dto = kul_ocr.service_layer.services.jobs.start_ocr_job_processing(
            str(job_id), uow=uow
        )
        return schemas.JobResponse.from_dto(job_dto)
    except Exception as e:
        job_dto = kul_ocr.service_layer.services.jobs.fail_ocr_job(
            str(job_id), str(e), uow=uow
        )
        return schemas.JobResponse.from_dto(job_dto)


@router.delete(
    "/ocr/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_ocr_job(
    job_id: UUID,
    uow: UnitOfWorkDep,
) -> Response:
    kul_ocr.service_layer.services.jobs.delete_ocr_job(str(job_id), uow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/ocr/jobs/{job_id}/retry",
    response_model=schemas.JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def retry_ocr_job(
    job_id: UUID,
    uow: UnitOfWorkDep,
) -> schemas.JobResponse:
    logger.info("Retry requested for OCR job %s", job_id)
    return schemas.JobResponse.from_dto(
        kul_ocr.service_layer.services.jobs.retry_ocr_job(str(job_id), uow)
    )


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
    job_dtos = kul_ocr.service_layer.services.jobs.get_ocr_jobs(
        uow=uow, status=status, document_id=str(document_id) if document_id else None
    )
    return schemas.JobListResponse(
        jobs=[schemas.JobResponse.from_dto(dto) for dto in job_dtos],
        total=len(job_dtos),
    )


@router.get(
    "/ocr/jobs/{job_id}",
    response_model=schemas.JobResponse,
    status_code=status.HTTP_200_OK,
)
def get_ocr_job_by_id(
    job_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schemas.JobResponse:
    return schemas.JobResponse.from_dto(
        kul_ocr.service_layer.services.jobs.get_ocr_job_response(str(job_id), uow)
    )


@router.post("/ocr/jobs/{job_id}/cancel")
def cancel_ocr_job(
    job_id: UUID,
    uow: UnitOfWorkDep,
) -> schemas.JobResponse:
    try:
        return schemas.JobResponse.from_dto(
            kul_ocr.service_layer.services.jobs.cancel_ocr_job(str(job_id), uow)
        )
    except kul_ocr.adapters.database.repository.OCRJobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


app.include_router(router)

exception_handlers.register_handlers(app)
