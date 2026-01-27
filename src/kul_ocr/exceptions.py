from typing import Any


class DomainException(Exception):
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context
        self.context["code"] = self.code
