# OCR Image Processor

## Goal
A command-line tool designed for OCR processing of image files using the Tesseract engine.

---

## Prerequisites

1.  **Python >=3.8**
2.  **Tesseract OCR Engine** https://github.com/madmaze/pytesseract

## USAGE

# Install Tesseract
# src/ocr/config.py
DEFAULT_TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Command
python main.py input_path [OPTIONS]

| Option          | Parameter | Description                                   | Default       |
| --------------- | --------- | --------------------------------------------- | ------------- |
| `-o, --output`  | DIR       | Output directory where results are saved.     | `ocr_results` |
| `-l, --lang`    | LANG_CODE | Tesseract language code (e.g., `eng`, `pol`). | `eng`         |
| `-t, --timeout` | SECONDS   | Timeout for processing a single image.        | `30`          |


# Tests
pip install pytest
To execute all tests and confirm code functionality

# Output Files
The program generates the following files in the specified output directory:

results.json: A structured file containing execution metadata (success/fail count, total time) and detailed results for each image.

results.txt: Concatenated plain text output from all successfully processed images.

results.md: Markdown format of the concatenated text.
