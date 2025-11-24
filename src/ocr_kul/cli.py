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
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Save result to file"
)
def process(image_path: Path, preprocess: bool, output: Path | None):
    """Process a single image and extract text.

    Example:
        ocr process image.png
        ocr process image.png --preprocess
        ocr process image.png -o result.txt
    """
    from src.ocr_kul import io_utils, preprocessing, engine

    try:
        # 1. Load image using io_utils.load_image()
        img = io_utils.load_image(image_path)

        # 2. If preprocess flag is set, apply preprocessing.enhance_image()
        if preprocess:
            img = preprocessing.enhance_image(img)

        # 3. Create TesseractOCREngine instance
        engine_instance = engine.TesseractOCREngine()

        # 4. Call engine.process(image) to get OCRResult
        result = engine_instance.process(img)

        # 5. Print result.text and result.confidence
        click.echo(f"Extracted Text:\n{result.text}")
        click.echo(f"Confidence: {result.confidence:.2f}%")

        # 6. If output path provided, save text to file
        if output is not None:
            output.write_text(result.text)
            click.echo(f"Result saved to: {output}")

    # 7. Handle errors gracefully with try/except
    except Exception as e:
        click.echo(f"Error processing image: {e}", err=True)


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
    from ocr_kul import io_utils, preprocessing, engine

    # 1. Get all image files using io_utils.get_image_files()
    image_files = io_utils.get_image_files(directory)

    # 2. Create TesseractOCREngine instance
    engine_instance = engine.TesseractOCREngine()
    # 3. Loop through images:
    with output.open("a") as f:
        success_count = 0
        for idx, image_path in enumerate(image_files, start=1):
            try:
                #    - Load image
                img = io_utils.load_image(image_path)

                #    - Optionally preprocess
                if preprocess:
                    img = preprocessing.enhance_image(img)

                #    - Process with engine
                result = engine_instance.process(img)

                #    - Write result to output file
                f.write(
                    f"{image_path.name}: {result.text} (confidence: {result.confidence:.2f}%)\n"
                )

                # 4. Show progress (e.g., "Processing 5/10 images...")
                click.echo(f"Processed {idx}/{len(image_files)}: {image_path.name}")

                success_count += 1

            # 5. Handle errors for individual images (skip and continue)
            except Exception as e:
                click.echo(f"Error processing {image_path.name}: {e}", err=True)
                import traceback

                traceback.print_exc()
                continue

    # 6. Print summary: "Processed X/Y images successfully"
    click.echo(f"Processed {success_count}/{len(image_files)} images successfully")


@cli.command()
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Directory to save processed images",
)
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
    from ocr_kul import io_utils, preprocessing

    # 1. Load image
    img = io_utils.load_image(image_path)

    # 2. Apply each preprocessing function:
    #    - preprocessing.enhance_image()
    enhanced_img = preprocessing.enhance_image(img)
    #    - preprocessing.resize_image()
    resized_img = preprocessing.resize_image(img)
    #    - preprocessing.binarize_image()
    binarized_img = preprocessing.binarize_image(img)

    # 3. Save each version with descriptive name
    base_dir = output_dir if output_dir is not None else image_path.parent
    base_dir.mkdir(parents=True, exist_ok=True)
    io_utils.save_image(img, base_dir / "original.png")
    io_utils.save_image(enhanced_img, base_dir / "enhanced.png")
    io_utils.save_image(resized_img, base_dir / "resized.png")
    io_utils.save_image(binarized_img, base_dir / "binarized.png")

    # 4. Print paths to saved images
    click.echo(f"Saved processed images to: {base_dir}")

    # 5. Optional: Show image info (size, mode, etc.)
    click.echo(f"Original image size: {img.size}, mode: {img.mode}")
    click.echo(f"Enhanced image size: {enhanced_img.size}, mode: {enhanced_img.mode}")
    click.echo(f"Resized image size: {resized_img.size}, mode: {resized_img.mode}")
    click.echo(
        f"Binarized image size: {binarized_img.size}, mode: {binarized_img.mode}"
    )


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
