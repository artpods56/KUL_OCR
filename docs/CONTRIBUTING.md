# Contributing to KUL OCR

Thank you for your interest in contributing! This project is developed by students at KUL.

## Getting Started

1. Fork the repository (or clone if you have access)
2. Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Ensure all checks pass

## Code Quality Standards

### Pre-commit Hooks

We use pre-commit hooks to maintain code quality. Install them:

```bash
pre-commit install
```

Run manually:
```bash
pre-commit run --all-files
```

### Tools We Use

- **Ruff**: Linting and formatting
- **Basedpyright**: Static type checking
- **Detect-secrets**: Prevents committing sensitive information
- **Beartype**: Runtime type checking

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=ocr_kul
```

## Submission Guidelines

1. Ensure your code passes all pre-commit checks
2. Add tests for new functionality
3. Update documentation if needed
4. Write clear commit messages following [Conventional Commits](CONVENTIONAL_COMMITS.md)
5. Submit a merge request

## Code Style

- Follow PEP 8 (enforced by Ruff)
- Use type hints (checked by Basedpyright)
- Write descriptive variable and function names
- Add docstrings for public functions and classes

## Questions?

Feel free to open an issue or reach out to the maintainers.
