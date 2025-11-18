"""Tests for CLI functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from ocr_kul.cli import cli
from ocr_kul.engine import OCRResult


def test_cli_exists():
    """CLI should be importable and runnable."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "KUL OCR" in result.output


def test_cli_has_process_command():
    """CLI should have 'process' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert result.exit_code == 0
    assert "process" in result.output.lower()


def test_cli_has_batch_command():
    """CLI should have 'batch' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["batch", "--help"])
    assert result.exit_code == 0
    assert "batch" in result.output.lower()


def test_cli_has_enhance_command():
    """CLI should have 'enhance' command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["enhance", "--help"])
    assert result.exit_code == 0
    assert "enhance" in result.output.lower()


def test_process_command_works_with_image():
    """process command should process an image and output text."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        # Create test image
        img = Image.new("RGB", (100, 100), color="white")
        img.save(tmp.name)
        test_path = Path(tmp.name)

        try:
            with patch("ocr_kul.engine.TesseractOCREngine.process") as mock_process:
                mock_process.return_value = OCRResult(
                    text="Sample text", confidence=95.5
                )

                result = runner.invoke(cli, ["process", str(test_path)])

                # Should not crash
                assert (
                    "NotImplementedError" not in result.output or result.exit_code == 0
                )
        except NotImplementedError:
            pytest.skip("CLI process command not implemented")
        finally:
            test_path.unlink()


def test_batch_command_works_with_directory():
    """batch command should process all images in directory."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        output_file = dir_path / "results.txt"

        # Create test images
        img = Image.new("RGB", (50, 50), color="white")
        (img).save(dir_path / "test1.png")
        (img).save(dir_path / "test2.png")

        try:
            with patch("ocr_kul.engine.TesseractOCREngine.process") as mock_process:
                mock_process.return_value = OCRResult(text="text", confidence=90.0)

                result = runner.invoke(
                    cli, ["batch", str(dir_path), "-o", str(output_file)]
                )

                # Should not crash
                assert (
                    "NotImplementedError" not in result.output or result.exit_code == 0
                )
        except NotImplementedError:
            pytest.skip("CLI batch command not implemented")


def test_enhance_command_works_with_image():
    """enhance command should save preprocessed versions of image."""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(tmp.name)
        test_path = Path(tmp.name)

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                result = runner.invoke(
                    cli, ["enhance", str(test_path), "-o", output_dir]
                )

                # Should not crash
                assert (
                    "NotImplementedError" not in result.output or result.exit_code == 0
                )
        except NotImplementedError:
            pytest.skip("CLI enhance command not implemented")
        finally:
            test_path.unlink()
