from typing import final

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from kul_ocr.adapters.database import repository
from kul_ocr.service_layer import parsing
from kul_ocr.service_layer.services import jobs
from kul_ocr.domain import exceptions


@final
class ExceptionResponseFactory:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def __call__(self, request: Request, exception: Exception) -> JSONResponse:
        return JSONResponse(
            content={"detail": getattr(exception, "message", str(exception))},
            status_code=self.status_code,
        )


def register_handlers(app: FastAPI):
    app.add_exception_handler(
        exceptions.UnsupportedFileTypeError,
        ExceptionResponseFactory(status.HTTP_400_BAD_REQUEST),
    )
    app.add_exception_handler(
        parsing.FileContentMismatchError,
        ExceptionResponseFactory(status.HTTP_422_UNPROCESSABLE_CONTENT),
    )
    app.add_exception_handler(
        exceptions.FileSizeExceededError,
        ExceptionResponseFactory(status.HTTP_413_CONTENT_TOO_LARGE),
    )
    app.add_exception_handler(
        repository.DocumentNotFoundError,
        ExceptionResponseFactory(status.HTTP_404_NOT_FOUND),
    )

    app.add_exception_handler(
        jobs.DuplicateOCRJobError,
        ExceptionResponseFactory(status.HTTP_409_CONFLICT),
    )

    app.add_exception_handler(
        exceptions.InvalidJobStatusTransitionError,
        ExceptionResponseFactory(status.HTTP_400_BAD_REQUEST),
    )

    app.add_exception_handler(
        exceptions.UnknownJobStatusError,
        ExceptionResponseFactory(status.HTTP_400_BAD_REQUEST),
    )

    app.add_exception_handler(
        repository.OCRJobNotFoundError,
        ExceptionResponseFactory(status.HTTP_404_NOT_FOUND),
    )

    app.add_exception_handler(
        ValueError,
        ExceptionResponseFactory(status.HTTP_400_BAD_REQUEST),
    )
