"""KUL OCR - A production-ready OCR service with preprocessing capabilities."""

from beartype.claw import beartype_this_package

from ocr_kul import config, engine, io_utils, preprocessing

beartype_this_package()

__all__ = ["config", "engine", "io_utils", "preprocessing"]
