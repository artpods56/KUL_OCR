# tests/unit/domain/model/test_result.py

import time
from datetime import datetime

from ocr_kul.domain.model import (
    OCRResult,
    SimpleOCRValue,
    SinglePageOcrValue,
    MultiPageOcrValue,
)


class TestSimpleOCRValue:
    """Tests for SimpleOCRValue - single string content"""

    def test_simple_ocr_value_creation(self):
        value = SimpleOCRValue(content="Hello, World!")

        assert value.content == "Hello, World!"

    def test_simple_ocr_value_empty_content(self):
        value = SimpleOCRValue(content="")

        assert value.content == ""

    def test_simple_ocr_value_multiline_content(self):
        content = "Line 1\nLine 2\nLine 3"
        value = SimpleOCRValue(content=content)

        assert value.content == content
        assert "\n" in value.content


class TestSinglePageOcrValue:
    """Tests for SinglePageOcrValue - single page with page number"""

    def test_single_page_ocr_value_creation(self):
        value = SinglePageOcrValue(page_number=1, content="Page 1 text")

        assert value.page_number == 1
        assert value.content == "Page 1 text"

    def test_single_page_ocr_value_page_zero(self):
        # Some systems use 0-based page indexing
        value = SinglePageOcrValue(page_number=0, content="First page")

        assert value.page_number == 0
        assert value.content == "First page"

    def test_single_page_ocr_value_large_page_number(self):
        value = SinglePageOcrValue(page_number=999, content="Last page")

        assert value.page_number == 999

    def test_single_page_ocr_value_empty_content(self):
        value = SinglePageOcrValue(page_number=1, content="")

        assert value.page_number == 1
        assert value.content == ""


class TestMultiPageOcrValue:
    """Tests for MultiPageOcrValue - multiple pages"""

    def test_multi_page_ocr_value_creation(self):
        pages = [
            SinglePageOcrValue(page_number=1, content="Page 1"),
            SinglePageOcrValue(page_number=2, content="Page 2"),
            SinglePageOcrValue(page_number=3, content="Page 3"),
        ]
        value = MultiPageOcrValue(content=pages)

        assert len(value.content) == 3
        assert value.content[0].page_number == 1
        assert value.content[0].content == "Page 1"
        assert value.content[2].page_number == 3

    def test_multi_page_ocr_value_single_page(self):
        # Edge case: multipage with only one page
        pages = [SinglePageOcrValue(page_number=1, content="Only page")]
        value = MultiPageOcrValue(content=pages)

        assert len(value.content) == 1
        assert value.content[0].content == "Only page"

    def test_multi_page_ocr_value_empty_list(self):
        # Edge case: empty document
        value = MultiPageOcrValue(content=[])

        assert len(value.content) == 0

    def test_multi_page_ocr_value_iteration(self):
        pages = [
            SinglePageOcrValue(page_number=i, content=f"Page {i}") for i in range(1, 6)
        ]
        value = MultiPageOcrValue(content=pages)

        # Test iteration
        page_numbers = [page.page_number for page in value.content]
        assert page_numbers == [1, 2, 3, 4, 5]


class TestOCRResult:
    """Tests for OCRResult entity"""

    def test_ocr_result_with_simple_value(self):
        content = SimpleOCRValue(content="Extracted text")
        result = OCRResult(id="result-1", job_id="job-1", content=content)

        assert result.id == "result-1"
        assert result.job_id == "job-1"
        assert result.content.content == "Extracted text"
        assert isinstance(result.creation_time, datetime)

    def test_ocr_result_with_single_page_value(self):
        content = SinglePageOcrValue(page_number=1, content="Page content")
        result = OCRResult(id="result-2", job_id="job-2", content=content)

        assert result.id == "result-2"
        assert result.job_id == "job-2"
        assert result.content.page_number == 1
        assert result.content.content == "Page content"

    def test_ocr_result_with_multi_page_value(self):
        pages = [
            SinglePageOcrValue(page_number=1, content="Page 1"),
            SinglePageOcrValue(page_number=2, content="Page 2"),
        ]
        content = MultiPageOcrValue(content=pages)
        result = OCRResult(id="result-3", job_id="job-3", content=content)

        assert result.id == "result-3"
        assert len(result.content.content) == 2
        assert result.content.content[0].content == "Page 1"
        assert result.content.content[1].content == "Page 2"

    def test_ocr_results_have_unique_timestamps(self):
        content1 = SimpleOCRValue(content="Text 1")
        result1 = OCRResult(id="1", job_id="job-1", content=content1)

        time.sleep(0.01)

        content2 = SimpleOCRValue(content="Text 2")
        result2 = OCRResult(id="2", job_id="job-2", content=content2)

        assert result1.creation_time < result2.creation_time

    def test_ocr_result_creation_time_auto_generated(self):
        content = SimpleOCRValue(content="Test")
        before = datetime.now()
        result = OCRResult(id="1", job_id="job-1", content=content)
        after = datetime.now()

        assert before <= result.creation_time <= after

    def test_ocr_result_with_custom_creation_time(self):
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        content = SimpleOCRValue(content="Test")
        result = OCRResult(
            id="1", job_id="job-1", content=content, creation_time=custom_time
        )

        assert result.creation_time == custom_time

    def test_ocr_result_multiple_jobs_same_document(self):
        # Test that different jobs can have different results
        content1 = SimpleOCRValue(content="First attempt")
        result1 = OCRResult(id="result-1", job_id="job-1", content=content1)

        content2 = SimpleOCRValue(content="Second attempt")
        result2 = OCRResult(id="result-2", job_id="job-2", content=content2)

        assert result1.job_id != result2.job_id
        assert result1.content.content != result2.content.content
