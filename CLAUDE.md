# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KUL OCR is an asynchronous OCR service built using clean architecture principles. The service processes documents (PDFs and images) using Tesseract OCR with Celery-based task queuing and supports multiple storage backends.

## Essential Commands

### Dependency Management
```bash
# Install all dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=kul_ocr

# Run a specific test file
uv run pytest tests/unit/test_example.py

# Run a specific test
uv run pytest tests/unit/test_example.py::test_function_name

# Run tests matching a pattern
uv run pytest -k "test_pattern"
```

### Code Quality
```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Format and lint code (Ruff)
uv run ruff check --fix
uv run ruff format

# Type checking (Basedpyright)
uv run basedpyright

# Check for secrets
detect-secrets scan
```

### Running Services
```bash
# Start RabbitMQ (required for Celery)
docker-compose up -d

# Run the FastAPI application
uv run fastapi dev src/kul_ocr/entrypoints/api.py

# Start Celery worker
uv run celery -A kul_ocr.entrypoints.celery_app worker --loglevel=info
```

## Architecture

### Clean Architecture Layers

The codebase follows clean architecture with strict separation of concerns:

1. **Domain Layer** (`src/kul_ocr/domain/`)
   - `model.py`: Core entities (Document, Job, Result) and value objects
   - `ports.py`: Abstract interfaces (OCREngine, DocumentLoader, FileStorage)
   - `exceptions.py`: Domain-specific exceptions
   - `structs.py`: Data transfer structures

2. **Service Layer** (`src/kul_ocr/service_layer/`)
   - `services.py`: Business logic orchestration
   - `uow.py`: Unit of Work pattern for transaction management
   - `parsing.py`: Input parsing utilities
   - Services coordinate between domain and adapters without knowing implementation details

3. **Adapters Layer** (`src/kul_ocr/adapters/`)
   - `database/`: SQLAlchemy ORM mappings and repositories
   - `ocr/`: OCR engine implementations (Tesseract)
   - `loaders/`: Document loaders (PDF, image)
   - `storages/`: File storage implementations (local, future: S3, etc.)
   - Adapters implement domain ports and handle external dependencies

4. **Entrypoints** (`src/kul_ocr/entrypoints/`)
   - `api.py`: FastAPI REST endpoints
   - `tasks.py`: Celery task definitions
   - `celery_app.py`: Celery application setup
   - `schemas.py`: API request/response models
   - `dependencies.py`: FastAPI dependency injection
   - `exception_handlers.py`: HTTP exception handling

### Key Design Patterns

- **Unit of Work**: Transaction management across repositories (`uow.py`)
- **Repository Pattern**: Abstract data access in `adapters/database/repository.py`
- **Dependency Injection**: FastAPI dependencies provide configured instances
- **Ports and Adapters**: Domain defines interfaces, adapters implement them

### Important Architecture Rules

1. **Domain independence**: Domain layer has NO external dependencies (except stdlib, msgspec, SQLAlchemy for annotations)
2. **Dependency direction**: Always flows inward: Entrypoints → Services → Domain ← Adapters
3. **Ports define contracts**: Domain defines what it needs via abstract ports, adapters implement them
4. **Services orchestrate**: Business logic lives in service layer, not entrypoints or adapters

## Configuration

Configuration uses Pydantic Settings with environment variables:

- Prefix: `KUL_OCR_`
- Config file: `.env` (copy from `.env.example`)
- Key settings:
  - `KUL_OCR_DB_SCHEME`: Database type (sqlite, mysql, postgres)
  - `KUL_OCR_STORAGE_TYPE`: Storage backend (local, future: s3)
  - `KUL_OCR_STORAGE_ROOT`: Root directory for file storage
  - `KUL_OCR_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

See `src/kul_ocr/config.py` for complete configuration schema.

## Type Safety

This project enforces strict runtime and static type checking:

- **Runtime**: Beartype validates function signatures at runtime
- **Static**: Basedpyright checks types at development time
- **Testing**: pytest-beartype validates types during tests

When adding functions:
- Always add type hints
- Use `from kul_ocr.utils.misc import nobeartype` decorator only when beartype conflicts with libraries (e.g., Pydantic)

## Database & ORM

- **ORM**: SQLAlchemy with classical mapping (not declarative)
- **Mappers**: Defined in `adapters/database/orm.py`, started via `orm.start_mappers()`
- **Migrations**: [TODO - check if Alembic is configured]
- **Repositories**: All database access goes through repository pattern

## Testing Strategy

- **Structure**: `tests/unit/` for unit tests, `tests/integration/` for integration tests
- **Fixtures**: Shared fixtures in `tests/conftest.py`
- **Fakes**: Test doubles in `tests/fakes/`
- **Factories**: Object factories in `tests/factories.py`
- **Environment**: Test environment variables set in `pytest.ini`

## Commit Conventions

Follow conventional commits (enforced by pre-commit hook):

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `perf`: Performance improvements
- `test`: Test additions/modifications
- `docs`: Documentation only
- `build`: Build system/dependencies
- `ops`: Infrastructure/deployment
- `chore`: Miscellaneous

Format: `type(optional-scope): description`

Examples:
```
feat(api): add document download endpoint
fix(ocr): handle empty PDF pages
refactor(storage): extract file path logic
```

See `docs/CONVENTIONAL_COMMITS.md` for full specification.

## File Storage

Storage is abstracted via `ports.FileStorage`:
- Currently supports local filesystem
- Files organized by document ID
- Configurable root directory via `KUL_OCR_STORAGE_ROOT`
- Create `./storage` directory before running (default location)

## OCR Processing Flow

1. Client uploads document via POST `/documents`
2. Document saved to storage, record created in database
3. Client creates OCR job via POST `/ocr/jobs`
4. FastAPI triggers Celery task `process_ocr_job_task`
5. Celery worker:
   - Loads document from storage
   - Processes with OCR engine (page-by-page for PDFs)
   - Saves Result to database
   - Updates job status
6. Client polls job status via GET `/ocr/jobs`

## Adding New Features

When adding features, respect the architecture:

1. **New entity/value object**: Add to `domain/model.py`
2. **New external dependency**: Define port in `domain/ports.py`, implement in `adapters/`
3. **New business logic**: Add to `service_layer/services.py`
4. **New API endpoint**: Add to `entrypoints/api.py` with schema in `entrypoints/schemas.py`
5. **New async task**: Add to `entrypoints/tasks.py`

Always create/update tests alongside implementation.

## Search and Exploration

When searching the codebase, prefer `mgrep` (semantic search) over `grep`:

```bash
# Good
mgrep "How are OCR jobs processed?"
mgrep "Where are database transactions managed?" src/kul_ocr

# Avoid
grep -r "process_ocr"  # Use mgrep instead
```
