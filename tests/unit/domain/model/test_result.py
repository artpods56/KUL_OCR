# tests/unit/domain/model/test_result.py

import time
from datetime import datetime

from kul_ocr.domain.model import (
    Result,
    BoundingBox,
    TextPart,
    PagePart,
    PageMetadata,
    PageRef,
    ProcessedPage,
)


class TestBoundingBox:
    """Tests for BoundingBox value object."""

    def test_bounding_box_creation(self):
        bbox = BoundingBox(x_min=10.0, y_min=20.0, x_max=100.0, y_max=200.0)

        assert bbox.x_min == 10.0
        assert bbox.y_min == 20.0
        assert bbox.x_max == 100.0
        assert bbox.y_max == 200.0

    def test_bounding_box_zero_coords(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=0.0, y_max=0.0)

        assert bbox.x_min == 0.0
        assert bbox.y_min == 0.0
        assert bbox.x_max == 0.0
        assert bbox.y_max == 0.0


class TestTextPart:
    """Tests for TextPart value object."""

    def test_text_part_creation(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0)
        text_part = TextPart(
            text="Hello, World!", bbox=bbox, confidence=0.95, level="block"
        )

        assert text_part.text == "Hello, World!"
        assert text_part.confidence == 0.95
        assert text_part.level == "block"

    def test_text_part_optional_confidence(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0)
        text_part = TextPart(text="Text", bbox=bbox, confidence=None)

        assert text_part.confidence is None

    def test_text_part_default_level(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0)
        text_part = TextPart(text="Text", bbox=bbox)

        assert text_part.level == "block"


class TestPageMetadata:
    """Tests for PageMetadata value object."""

    def test_page_metadata_creation(self):
        metadata = PageMetadata(page_number=1, width=1000, height=1200)

        assert metadata.page_number == 1
        assert metadata.width == 1000
        assert metadata.height == 1200
        assert metadata.rotation == 0  # default

    def test_page_metadata_with_rotation(self):
        metadata = PageMetadata(page_number=1, width=1000, height=1200, rotation=90)

        assert metadata.rotation == 90


class TestPagePart:
    """Tests for PagePart value object."""

    def test_page_part_creation(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0)
        text_part = TextPart(text="Hello", bbox=bbox)
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=[text_part], metadata=metadata)

        assert len(page_part.parts) == 1
        assert page_part.parts[0].text == "Hello"
        assert page_part.metadata.page_number == 1

    def test_page_part_multiple_text_parts(self):
        parts = [
            TextPart(
                text=f"Line {i}",
                bbox=BoundingBox(
                    x_min=float(i * 10),
                    y_min=0.0,
                    x_max=float((i + 1) * 10),
                    y_max=20.0,
                ),
            )
            for i in range(3)
        ]
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=parts, metadata=metadata)

        assert len(page_part.parts) == 3
        assert page_part.parts[0].text == "Line 0"
        assert page_part.parts[2].text == "Line 2"

    def test_page_part_full_text_property(self):
        parts = [
            TextPart(text="Line 1", bbox=BoundingBox(0.0, 0.0, 100.0, 20.0)),
            TextPart(text="Line 2", bbox=BoundingBox(0.0, 20.0, 100.0, 40.0)),
            TextPart(text="Line 3", bbox=BoundingBox(0.0, 40.0, 100.0, 60.0)),
        ]
        metadata = PageMetadata(page_number=1, width=100, height=60)
        page_part = PagePart(parts=parts, metadata=metadata)

        full_text = page_part.full_text
        assert full_text == "Line 1Line 2Line 3"


class TestPageRef:
    """Tests for PageRef value object."""

    def test_page_ref_creation(self):
        ref = PageRef(document_id="doc-123", index=5)

        assert ref.document_id == "doc-123"
        assert ref.index == 5


class TestProcessedPage:
    """Tests for ProcessedPage value object."""

    def test_processed_page_creation(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0)
        text_part = TextPart(text="Hello", bbox=bbox)
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=[text_part], metadata=metadata)
        ref = PageRef(document_id="doc-123", index=0)

        processed_page = ProcessedPage(ref=ref, result=page_part)

        assert processed_page.ref.document_id == "doc-123"
        assert processed_page.ref.index == 0
        assert processed_page.result.metadata.page_number == 1
        assert processed_page.result.parts[0].text == "Hello"


class TestOCRResult:
    """Tests for Result entity"""

    def test_ocr_result_creation(self):
        bbox = BoundingBox(x_min=0.0, y_min=0.0, x_max=100.0, y_max=50.0)
        text_part = TextPart(text="Hello", bbox=bbox)
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=[text_part], metadata=metadata)
        ref = PageRef(document_id="doc-123", index=0)
        processed_page = ProcessedPage(ref=ref, result=page_part)

        result = Result(id="result-1", job_id="job-1", content=[processed_page])

        assert result.id == "result-1"
        assert result.job_id == "job-1"
        assert len(result.content) == 1
        assert isinstance(result.creation_time, datetime)

    def test_ocr_result_with_multiple_pages(self):
        pages = []
        for i in range(3):
            text_part = TextPart(
                text=f"Page {i + 1}",
                bbox=BoundingBox(0.0, 0.0, 100.0, 50.0),
            )
            metadata = PageMetadata(page_number=i, width=1000, height=1200)
            page_part = PagePart(parts=[text_part], metadata=metadata)
            ref = PageRef(document_id="doc-123", index=i)
            processed_page = ProcessedPage(ref=ref, result=page_part)
            pages.append(processed_page)

        result = Result(id="result-1", job_id="job-1", content=pages)

        assert len(result.content) == 3
        assert result.content[0].result.parts[0].text == "Page 1"
        assert result.content[2].result.parts[0].text == "Page 3"

    def test_ocr_results_have_unique_timestamps(self):
        text_part = TextPart(text="Text 1", bbox=BoundingBox(0.0, 0.0, 100.0, 50.0))
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=[text_part], metadata=metadata)
        ref = PageRef(document_id="doc-123", index=0)
        processed_page = ProcessedPage(ref=ref, result=page_part)

        result1 = Result(id="1", job_id="job-1", content=[processed_page])

        time.sleep(0.01)

        text_part2 = TextPart(text="Text 2", bbox=BoundingBox(0.0, 0.0, 100.0, 50.0))
        page_part2 = PagePart(parts=[text_part2], metadata=metadata)
        processed_page2 = ProcessedPage(ref=ref, result=page_part2)

        result2 = Result(id="2", job_id="job-2", content=[processed_page2])

        assert result1.creation_time < result2.creation_time

    def test_ocr_result_creation_time_auto_generated(self):
        text_part = TextPart(text="Test", bbox=BoundingBox(0.0, 0.0, 100.0, 50.0))
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=[text_part], metadata=metadata)
        ref = PageRef(document_id="doc-123", index=0)
        processed_page = ProcessedPage(ref=ref, result=page_part)

        before = datetime.now()
        result = Result(id="1", job_id="job-1", content=[processed_page])
        after = datetime.now()

        assert before <= result.creation_time <= after

    def test_ocr_result_with_custom_creation_time(self):
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        text_part = TextPart(text="Test", bbox=BoundingBox(0.0, 0.0, 100.0, 50.0))
        metadata = PageMetadata(page_number=1, width=1000, height=1200)
        page_part = PagePart(parts=[text_part], metadata=metadata)
        ref = PageRef(document_id="doc-123", index=0)
        processed_page = ProcessedPage(ref=ref, result=page_part)

        result = Result(
            id="1",
            job_id="job-1",
            content=[processed_page],
            creation_time=custom_time,
        )

        assert result.creation_time == custom_time
