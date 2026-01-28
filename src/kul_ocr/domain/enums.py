from enum import Enum


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(Enum):
    PDF = "application/pdf"
    PNG = "image/png"
    JPG = "image/jpeg"
    JPEG = "image/jpeg"
    WEBP = "image/webp"

    @property
    def extension(self) -> str:
        return self.name.lower()

    @property
    def dot_extension(self) -> str:
        return "." + self.extension

    @property
    def is_image(self) -> bool:
        return self.value.startswith("image/")


class DocumentStatus(Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class OutboxEventType(Enum):
    JOB_SCHEDULING = "job_scheduling"
    DOCUMENT_UPLOAD = "document_upload"
