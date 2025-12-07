import pytest
from PIL import Image
from kul_ocr.domain.structs import PageInput


class TestPageInput:
    """Comprehensive tests for the PageInput dataclass."""

    def test_can_create_page_input(self):
        """Shpuld create PageInput class."""
        image = Image.new("RGB", (100, 100))
        page_input = PageInput(image, page_number=1, original_document_id="doc-123")
        assert page_input.image == image
        assert page_input.page_number == 1
        assert page_input.original_document_id == "doc-123"

    def test_page_input_fields_are_accessible(self):
        """Should be able to access all fields after creation."""
        image = Image.new("L", (50, 50))
        page_input = PageInput(
            image=image, page_number=5, original_document_id="doc-xyz"
        )
        assert page_input.image.size == (50, 50)
        assert page_input.page_number == 5
        assert page_input.original_document_id == "doc-xyz"

    def test_page_input_with_page_number_zero(self):
        """Should be able to access page number 0."""
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(image=image, page_number=0, original_document_id="doc-0")
        assert page_input.page_number == 0

    def test_page_input_with_negative_page_number(self):
        """Should be able to access page with negative number."""
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(
            image=image, page_number=-1, original_document_id="doc-neg"
        )
        assert page_input.page_number == -1

    def test_page_input_with_large_number(self):
        """Should be able to access large number."""
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(
            image=image, page_number=9999, original_document_id="doc-large"
        )
        assert page_input.page_number == 9999

    def test_page_input_with_different_image_modes(self):
        """Should work with diffrent PIL Image modes."""
        for mode in ["RGB", "L", "RGBA"]:
            image = Image.new(mode, (10, 10))
            page_input = PageInput(
                image=image, page_number=1, original_document_id="doc-{mode}"
            )
            assert page_input.image.mode == mode

    def test_page_input_with_different_image_sizes(self):
        """Should work with diffrent size of image."""
        for size in [(10, 10), (5000, 5000), (100, 500)]:
            image = Image.new("RGB", size)
            page_input = PageInput(
                image=image,
                page_number=1,
                original_document_id=f"doc-{size[0]}x{size[1]}",
            )
            assert page_input.image.size == size

    def test_page_input_with_empty_document_id(self):
        """Should be able to access empty string as document_id."""
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(image=image, page_number=1, original_document_id="")
        assert page_input.original_document_id == ""

    def test_page_input_with_long_document_id(self):
        """Should be able to access long string as document_id."""
        long_id = "a" * 1000
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(image=image, page_number=1, original_document_id=long_id)
        assert page_input.original_document_id == long_id

    def test_page_input_with_special_characters_in_document_id(self):
        """Should be able to access string with special characters as document_id."""
        special_id = "doc-!@#$%^&*()_+абвгд"
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(
            image=image, page_number=1, original_document_id=special_id
        )
        assert page_input.original_document_id == special_id

    def test_slots_prevents_dynamic_attributes(self):
        """slots=True shoulld prevent adding new attributes"""
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(image=image, page_number=1, original_document_id="doc-1")
        with pytest.raises(AttributeError):
            page_input.new_field = "not allowed"

    def test_can_modify_existing_attributes(self):
        """Dataclass is mutable by default; existing fields can be modified."""
        image = Image.new("RGB", (10, 10))
        page_input = PageInput(image=image, page_number=1, original_document_id="doc-1")
        new_image = Image.new("L", (5, 5))
        page_input.image = new_image
        page_input.page_number = 42
        page_input.original_document_id = "doc-updated"

        assert page_input.image == new_image
        assert page_input.page_number == 42
        assert page_input.original_document_id == "doc-updated"
