<div align="center">

# KUL | OCR


**Optical Character Recognition Service for KUL**

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![beartype](https://raw.githubusercontent.com/beartype/beartype-assets/main/badge/bear-ified.svg)](https://github.com/beartype/beartype)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## About

OCR service built by students at the Catholic University of Lublin (KUL) for internal use.
Features asynchronous task processing, clean architecture, and runtime type safety.

## Quick Start

**Prerequisites:** Python 3.12+, Docker, CUDA capable GPU

```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env

# Create local storage directory (`storage` by default)
mkdir storage

# Install pre-commit hooks
pre-commit install

# Run tests
uv run pytest

# Run app
[TODO]

```

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions [TODO]
- [Contributing](docs/CONTRIBUTING.md) - How to contribute to the project
- [Conventional Commits](docs/CONVENTIONAL_COMMITS.md) - Commit message conventions
- [Architecture](docs/ARCHITECTURE.md) - System design and structure

## License

MIT License - see [LICENSE](LICENSE) file for details.
