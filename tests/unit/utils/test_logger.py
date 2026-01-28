from kul_ocr.utils import logger


def test_get_logger_returns_same_instance_per_name():
    log1 = logger.get_logger("kul_ocr.test")
    log2 = logger.get_logger("kul_ocr.test")

    assert log1._logger_factory_args == log2._logger_factory_args
    assert log1._logger_factory_args == ("kul_ocr.test",)
