"""Command-line interface for OCR service.

This CLI allows you to:
- Process single images
- Batch process directories
- Preview preprocessing effects
"""

from pathlib import Path
from typing import Union

import click
import sys
from ocr_kul import io_utils, preprocessing
from ocr_kul.engine import TesseractOCREngine


@click.group()
def cli():
    """KUL OCR - Optical Character Recognition CLI."""
    pass


@cli.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--preprocess", is_flag=True, help="Apply image enhancement before OCR")
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Save result to file"
)
def process(image_path: Path, preprocess: bool, output: Union[Path, None]):
    """Process a single image and extract text.

    Example:
        ocr process image.png
        ocr process image.png --preprocess
        ocr process image.png -o result.txt
    """
    image = None
    try:
        click.echo(f"Loading image: {image_path.name}")
        image = io_utils.load_image(image_path)

        if preprocess:
            click.echo("Applying image enhancements (preprocessing)...")
            image = preprocessing.enhance_image(image)

        ocr_engine = TesseractOCREngine()

        click.echo("Starting OCR processing...")
        result = ocr_engine.process(image)

        output_message = "\n=== OCR RESULT ===\n"
        output_message += f"Text: {result.text}\n"
        output_message += f"Confidence: {result.confidence:.2f}%\n"
        output_message += "=================\n"
        click.echo(output_message)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(result.text, encoding="utf-8")
            click.echo(f"Text saved to: {output}")

    except (FileNotFoundError, ValueError) as e:
        click.echo(
            f"\nI/O ERROR: Could not load or process image.\nDetails: {e}", err=True
        )
        sys.exit(1)
    except RuntimeError as e:
        click.echo(
            f"\nOCR ERROR: An error occurred in the OCR engine.\nDetails: {e}", err=True
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nUNEXPECTED ERROR: {e}", err=True)
        sys.exit(1)
    finally:
        if image is not None:
            image.close()


@cli.command()
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--preprocess", is_flag=True, help="Apply image enhancement before OCR")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file for results",
)
def batch(directory: Path, preprocess: bool, output: Path):
    """Process all images in a directory.

    Results are saved to a text file in format:
    filename.png: extracted text (confidence: 95.2%)

    Example:
        ocr batch ./images -o results.txt
        ocr batch ./images --preprocess -o results.txt
    """

    try:
        image_files = io_utils.get_image_files(directory)
        total_images = len(image_files)

        if total_images == 0:
            click.echo(f"No supported image files found in directory: {directory}")
            return

        click.echo(f"Found {total_images} images. Starting batch processing...")

        output.parent.mkdir(parents=True, exist_ok=True)
        results_list = []

        ocr_engine = TesseractOCREngine()

        processed_count = 0
        success_count = 0

        for i, image_path in enumerate(image_files, 1):
            processed_count = i
            image = None
            click.echo(f"Processing {i}/{total_images}: {image_path.name}...", nl=False)

            try:
                image = io_utils.load_image(image_path)
                if preprocess:
                    image = preprocessing.enhance_image(image)
                result = ocr_engine.process(image)

                result_line = f"{image_path.name}: {result.text} (confidence: {result.confidence:.2f}%)"
                results_list.append(result_line)
                success_count += 1
                click.echo(" DONE.")

            except Exception as e:
                error_line = f"{image_path.name}: ERROR - Failed to process image. Details: {type(e).__name__} ({e})"
                results_list.append(error_line)
                click.echo(f" FAILED. ({type(e).__name__})")
                continue
            finally:
                if image is not None:
                    image.close()

        output.write_text("\n".join(results_list) + "\n", encoding="utf-8")

        click.echo(
            f"\n--- SUMMARY ---\n"
            f"Results saved to: {output}\n"
            f"Images processed: {processed_count}\n"
            f"Successes: {success_count}\n"
            f"Failures: {processed_count - success_count}\n"
            f"---------------"
        )
    except Exception as e:
        click.echo(
            f"\nBATCH PROCESSING ERROR: An unexpected error occurred.\nDetails: {e}",
            err=True,
        )
        sys.exit(1)


@cli.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Directory to save processed images",
    default="processed_previews",
)
def enhance(image_path: Path, output_dir: Union[Path, None]):
    """Preview preprocessing effects on an image.

    Saves multiple versions:
    - original.png
    - enhanced.png
    - resized.png (2x)
    - binarized.png

    Example:
        ocr enhance image.png
        ocr enhance image.png -o ./processed
    """
    if output_dir is None:
        output_dir = Path("processed_previews")

    original_image = None
    try:
        click.echo(f"Loading image: {image_path.name}")
        original_image = io_utils.load_image(image_path)

        output_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = []

        operations = [
            ("enhanced.png", lambda img: preprocessing.enhance_image(img)),
            (
                "resized_2x.png",
                lambda img: preprocessing.resize_image(img, scale_factor=2.0),
            ),
            ("binarized.png", lambda img: preprocessing.binarize_image(img)),
        ]

        original_output_path = output_dir / f"original_{image_path.name}"
        io_utils.save_image(original_image, original_output_path)
        saved_paths.append(original_output_path)

        for filename, func in operations:
            click.echo(f"Generating {filename}...")
            processed_image = func(original_image.copy())

            output_path = output_dir / filename
            io_utils.save_image(processed_image, output_path)
            saved_paths.append(output_path)
            processed_image.close()

        click.echo("\n--- Saved Preview Files ---\n")
        for path in saved_paths:
            click.echo(f"  - {path}")
        click.echo("\n---------------------------\n")

    except (FileNotFoundError, ValueError) as e:
        click.echo(
            f"\nI/O ERROR: Could not load or process image.\nDetails: {e}", err=True
        )
        sys.exit(1)
    except RuntimeError as e:
        click.echo(
            f"\nOCR ERROR: An error occurred in the OCR engine.\nDetails: {e}", err=True
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nUNEXPECTED ERROR: {e}", err=True)
        sys.exit(1)
    finally:
        if original_image is not None:
            original_image.close()


if __name__ == "__main__":
    cli()
