from typing import final

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kul_ocr.domain import exceptions


@final
class ExceptionResponseFactory:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def __call__(self, request: Request, exception: Exception) -> JSONResponse:
        return JSONResponse(
            content={"message": getattr(exception, "message", str(exception))},
            status_code=self.status_code,
        )


def register_handlers(app: FastAPI):
    app.add_exception_handler(
        exceptions.UnsupportedFileTypeError, ExceptionResponseFactory(400)
    )

    app.add_exception_handler(
        exceptions.InvalidJobStatusError, ExceptionResponseFactory(400)
    )
