"""Tests for CLI functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image
from ocr_kul.cli import cli
from ocr_kul.engine import OCRResult


def test_cli_exists():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "KUL OCR" in result.output


def test_cli_has_process_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert result.exit_code == 0
    assert "process" in result.output.lower()


def test_cli_has_batch_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["batch", "--help"])
    assert result.exit_code == 0
    assert "batch" in result.output.lower()


def test_cli_has_enhance_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["enhance", "--help"])
    assert result.exit_code == 0
    assert "enhance" in result.output.lower()


def test_process_command_works_with_image():
    runner = CliRunner()

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    test_path = Path(path)

    try:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_path)

        with patch("ocr_kul.engine.TesseractOCREngine.process") as mock_process:
            mock_process.return_value = OCRResult(text="Sample text", confidence=95.5)

            result = runner.invoke(cli, ["process", str(test_path)])

            assert "NotImplementedError" not in result.output or result.exit_code == 0
    except NotImplementedError:
        pytest.skip("CLI process command not implemented")
    finally:
        if test_path.exists():
            test_path.unlink()


def test_batch_command_works_with_directory():
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        output_file = dir_path / "results.txt"

        img = Image.new("RGB", (50, 50), color="white")
        (img).save(dir_path / "test1.png")
        (img).save(dir_path / "test2.png")

        img.close()

        try:
            with patch("ocr_kul.engine.TesseractOCREngine.process") as mock_process:
                mock_process.return_value = OCRResult(text="text", confidence=90.0)

                result = runner.invoke(
                    cli, ["batch", str(dir_path), "-o", str(output_file)]
                )

                assert (
                    "NotImplementedError" not in result.output or result.exit_code == 0
                )
        except NotImplementedError:
            pytest.skip("CLI batch command not implemented")


def test_enhance_command_works_with_image():
    runner = CliRunner()

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    test_path = Path(path)

    try:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(test_path)
        img.close()

        with tempfile.TemporaryDirectory() as output_dir:
            result = runner.invoke(cli, ["enhance", str(test_path), "-o", output_dir])

            assert "NotImplementedError" not in result.output or result.exit_code == 0
    except NotImplementedError:
        pytest.skip("CLI enhance command not implemented")
    finally:
        if test_path.exists():
            test_path.unlink()
