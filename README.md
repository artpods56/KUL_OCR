# KUL OCR

This repository contains an OCR application developed for KUL.

## Project Structure

kul_ocr/
├── src/
│ └── ocr_kul/ # source code
├── tests/ # test files
├── pyproject.toml # project configuration
├── uv.lock # locked dependencies
└── README.md

## Setup

1. Make sure you have Python 3.12 installed.

2. Activate your virtual environment:

```bash
source .venv/bin/activate
```

3. Install the project in editable mode:

```bash
uv pip install -e .
```

## Usage

You can import the package anywhere in your project:

```python
from ocr_kul import task2_ocr_mkr
```

## Notes

The project uses uv for dependency management.
All source code lives in src/ocr_kul/, which allows proper installation as a Python package.