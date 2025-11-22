"""Command-line interface for OCR service.

This CLI allows you to:
- Process single images
- Batch process directories
- Preview preprocessing effects
"""
#sorry for stupid errors messages, but...I'm your father
from pathlib import Path

import click

from ocr_kul import config, engine, io_utils, preprocessing
#
# you really don't have to know what is happening here, focus on trying to implement all functions of the cli
# but if I don't know what is happening here, how am I supposed to make it work?
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

    try:
        image=io_utils.load_image(image)
        if process:
            image=preprocessing.enchance_image(image)
        ocr=engine.TesseractOCREngine()
        result=ocr.process(image)
        click.echo(f"Text: {result.text}")
        click.echo(f"\nConfidence: {result.confidence:.2f}%")
        
        if output:
            output.write_text(result.text, encoding="utf-8")
            click.echo(f"\Saved: {output}")
    except Exception as e:
        click.echo(f"Error; {e}",err=True)
        raise SystemExit(1)
        


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

    images=io_utils.get_image_files(directory)
    total=len(images)
    if total==0:
        click.echo("No images given, check your directory")
        return
    ocr=engine.TesseractOCREngine()
    success=0
    
    with output.open("w", encoding="utf-8") as file:
        for i, img_path in enumerate(images,start=1):
            click.echo("Processing {i}/{total}: {img_path.name}...:)")
            
            try:
                img=io_utils.load_image(img_path)
                if process:
                    image=preprocessing.enchance_image(image)
                result=ocr.process(img)
                file.write(
                    f"{img_path.name}: {result.text.strip()}"
                    f"(confidence: {result.confidence:.2f}%)"
                )
                success+=1
            except Exception as e:
                click.echo(f"Skipping {img_path.name}...why, could you ask...here's why: {e}")
    click.echp(f"\nLadies and gentlemen...we got them, {success}/{total} images")
    click.echo(f"Results saved to {output}")


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

    try:
        image=io_utils.load_image(image_path)
        if output_dir:
            output_dir.mkdir(parents=True,exist_ok=True)
        else:
            output_dir=image_path.parent
        saved_paths={}
        
        original_path=output_dir/"original.png"
        io_utils.save_image(image,original_path)
        saved_paths["original"]=original_path
        
        enhanced=preprocessing.enchance_image(image)
        enhanced_path=output_dir/"enhanced.png"
        io_utils.save_image(enhanced,enhanced_path)
        saved_paths["enhanced"]=enhanced_path
        
        resized=preprocessing.enchance_image(image)
        resized_path=output_dir/"resized.png"
        io_utils.save_image(resized,resized_path)
        saved_paths["resized"]=resized_path
        
        binarized=preprocessing.enchance_image(image)
        binarized_path=output_dir/"binaized.png"
        io_utils.save_image(binarized,binarized_path)
        saved_paths["binarized"]=binarized_path

        click.echo("Saved images:")
        for name, path in saved_paths.items():
            click.echo(f" {name}: {path}")
        click.echo(f"\nImage info: size={image.size}, mode={image.mode}")
    except Exception as e:
        click.echo(f"Error during enhancement: {e}",err=True)
        raise SystemExit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
