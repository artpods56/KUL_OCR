"""Command-line interface for OCR service.

This CLI allows you to:
- Process single images
- Batch process directories
- Preview preprocessing effects
"""

from pathlib import Path

import click

# from ocr_kul import config, engine, io_utils, preprocessing
#
# you really don't have to know what is happening here, focus on trying to implement all functions of the cli

@click.group()
def cli():
    """KUL OCR - Optical Character Recognition CLI."""
    pass


@cli.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--preprocess", is_flag=True, help="Apply image enhancement before OCR")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save result to file")
def process(image_path: Path, preprocess: bool, output: Path | None):
    """Process a single image and extract text.

    Example:
        ocr process image.png
        ocr process image.png --preprocess
        ocr process image.png -o result.txt
    """
    # TODO: Implement process command
    # 1. Load image using io_utils.load_image()
    # 2. If preprocess flag is set, apply preprocessing.enhance_image()
    # 3. Create TesseractOCREngine instance
    # 4. Call engine.process(image) to get OCRResult
    # 5. Print result.text and result.confidence
    # 6. If output path provided, save text to file
    # 7. Handle errors gracefully with try/except

    click.echo("TODO: Implement process command")
    raise NotImplementedError("TODO: Implement process command")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--preprocess", is_flag=True, help="Apply image enhancement before OCR")
@click.option("--output", "-o", type=click.Path(path_type=Path), required=True, help="Output file for results")
def batch(directory: Path, preprocess: bool, output: Path):
    """Process all images in a directory.

    Results are saved to a text file in format:
    filename.png: extracted text (confidence: 95.2%)

    Example:
        ocr batch ./images -o results.txt
        ocr batch ./images --preprocess -o results.txt
    """
    # TODO: Implement batch command
    # 1. Get all image files using io_utils.get_image_files()
    # 2. Create TesseractOCREngine instance
    # 3. Loop through images:
    #    - Load image
    #    - Optionally preprocess
    #    - Process with engine
    #    - Write result to output file
    # 4. Show progress (e.g., "Processing 5/10 images...")
    # 5. Handle errors for individual images (skip and continue)
    # 6. Print summary: "Processed X/Y images successfully"

    click.echo("TODO: Implement batch command")
    raise NotImplementedError("TODO: Implement batch command")


@cli.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), help="Directory to save processed images")
def enhance(image_path: Path, output_dir: Path | None):
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
    # TODO: Implement enhance command
    # 1. Load image
    # 2. Apply each preprocessing function:
    #    - preprocessing.enhance_image()
    #    - preprocessing.resize_image()
    #    - preprocessing.binarize_image()
    # 3. Save each version with descriptive name
    # 4. Print paths to saved images
    # 5. Optional: Show image info (size, mode, etc.)

    click.echo("TODO: Implement enhance command")
    raise NotImplementedError("TODO: Implement enhance command")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
