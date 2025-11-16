import abc

from ocr_kul.domain import model


class AbstractOCREngine(abc.ABC):
    @abc.abstractmethod
    def run_ocr_job(self, job: model.OCRJob) -> None:
        raise NotImplementedError
