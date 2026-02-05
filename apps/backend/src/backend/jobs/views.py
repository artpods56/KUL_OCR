from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from starlette import status
from starlette.responses import Response

from backend import dependencies
from . import schema, service

router = APIRouter()


@router.post(
    "",
    response_model=schema.JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ocr_job(
    request: schema.CreateJobRequest,
    uow: dependencies.UnitOfWorkDep,
) -> schema.JobResponse:
    return schema.JobResponse.from_dto(
        service.submit_ocr_job(str(request.document_id), uow)
    )


@router.post("/{job_id}/start")
def start_ocr_job(
    job_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schema.JobResponse:
    """Start processing an OCR job.

    Marks the job as PROCESSING and creates an outbox entry for reliable
    task scheduling. The outbox relay will pick up the entry and schedule
    the Celery task.
    """
    try:
        job_dto = service.start_ocr_job_processing(str(job_id), uow=uow)
        return schema.JobResponse.from_dto(job_dto)
    except Exception as e:
        job_dto = service.fail_ocr_job(str(job_id), str(e), uow=uow)
        return schema.JobResponse.from_dto(job_dto)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_ocr_job(
    job_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> Response:
    service.delete_ocr_job(str(job_id), uow)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{job_id}/retry",
    response_model=schema.JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def retry_ocr_job(
    job_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schema.JobResponse:
    return schema.JobResponse.from_dto(service.retry_ocr_job(str(job_id), uow))


@router.get("", response_model=schema.JobListResponse)
def list_ocr_jobs(
    uow: dependencies.UnitOfWorkDep,
    status: Annotated[
        str | None,
        Query(
            description="Filter by job status (pending, processing, completed, failed)"
        ),
    ] = None,
    document_id: Annotated[
        UUID | None, Query(description="Filter by document ID")
    ] = None,
    skip: Annotated[
        int,
        Query(
            ge=0,
            description="Number of items to skip (offset)",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum number of items to return (max: 100)",
        ),
    ] = 20,
) -> schema.JobListResponse:
    """List OCR jobs with optional filtering and pagination.

    Args:
        uow: Unit of work dependency
        status: Optional status filter
        document_id: Optional document ID filter
        skip: Pagination offset (default: 0)
        limit: Page size (default: 20, max: 100)

    Returns:
        Paginated list of jobs with metadata
    """
    job_dtos, total = service.get_ocr_jobs(
        uow=uow,
        status=status,
        document_id=str(document_id) if document_id else None,
        skip=skip,
        limit=limit,
    )

    return schema.JobListResponse(
        jobs=[schema.JobResponse.from_dto(dto) for dto in job_dtos],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{job_id}",
    response_model=schema.JobResponse,
    status_code=status.HTTP_200_OK,
)
def get_ocr_job_by_id(
    job_id: UUID,
    uow: dependencies.UnitOfWorkDep,
) -> schema.JobResponse:
    return schema.JobResponse.from_dto(service.get_ocr_job_response(str(job_id), uow))


@router.post("/{job_id}/cancel")
def cancel_ocr_job(
    job_id: UUID,
    task_runner: dependencies.TaskRunnerDep,
    uow: dependencies.UnitOfWorkDep,
) -> schema.JobResponse:
    return schema.JobResponse.from_dto(
        service.cancel_ocr_job(str(job_id), task_runner, uow)
    )
