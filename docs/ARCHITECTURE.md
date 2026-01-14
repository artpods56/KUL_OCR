# Architecture Overview

This document describes the multi-service architecture of the KUL OCR project, which separates the frontend (Django) and backend (FastAPI) into independent services.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Service Responsibilities](#service-responsibilities)
- [Dependency Management](#dependency-management)
- [Import Resolution](#import-resolution)
- [Docker Configuration](#docker-configuration)
- [Development Workflow](#development-workflow)
- [Communication Between Services](#communication-between-services)

## Architecture Diagram

```
┌─────────────────┐         HTTP/REST API         ┌──────────────────┐
│                 │ ◄──────────────────────────── │                  │
│  Django Frontend│                                │  FastAPI Backend │
│  (Web UI)       │ ──────────────────────────► │  (Business Logic)│
│                 │                                │                  │
└─────────────────┘                                └──────────────────┘
       │                                                    │
       │                                                    │
       ▼                                                    ▼
  Static Files                                    ┌─────────────────┐
                                                  │   PostgreSQL    │
                                                  │   Database      │
                                                  └─────────────────┘
                                                          │
                                                          │
                                                  ┌─────────────────┐
                                                  │  Celery Worker  │
                                                  │  (OCR Tasks)    │
                                                  └─────────────────┘
                                                          │
                                                          │
                                                  ┌─────────────────┐
                                                  │     Redis       │
                                                  │  (Task Queue)   │
                                                  └─────────────────┘
```

## Project Structure

The project is organized as a **monorepo** with separate packages for frontend and backend:

```
KUL_OCR/
├── pyproject.toml                 # Workspace root configuration
├── uv.lock                        # Shared dependency lock file
├── docker-compose.yaml            # Multi-service orchestration
├── .env.example                   # Environment variables template
│
├── backend/                       # FastAPI backend service
│   ├── pyproject.toml            # Backend dependencies
│   ├── Dockerfile                # Backend container image
│   ├── src/
│   │   └── kul_ocr/
│   │       ├── __init__.py
│   │       ├── domain/           # Business logic & models
│   │       │   ├── model.py
│   │       │   ├── ports.py
│   │       │   ├── structs.py
│   │       │   └── exceptions.py
│   │       ├── service_layer/    # Application services
│   │       │   ├── services.py
│   │       │   ├── uow.py
│   │       │   └── parsing.py
│   │       ├── adapters/         # External integrations
│   │       │   ├── database/
│   │       │   ├── ocr/
│   │       │   ├── storages/
│   │       │   └── loaders/
│   │       ├── entrypoints/      # API endpoints
│   │       │   ├── api.py
│   │       │   ├── celery_app.py
│   │       │   ├── dependencies.py
│   │       │   └── schemas.py
│   │       └── utils/
│   └── tests/
│
└── frontend/                      # Django frontend service
    ├── pyproject.toml            # Frontend dependencies
    ├── Dockerfile                # Frontend container image
    ├── manage.py                 # Django management script
    ├── frontend_app/             # Django project settings
    │   ├── __init__.py
    │   ├── settings.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    ├── web/                      # Main Django app (UI)
    │   ├── __init__.py
    │   ├── views.py              # View controllers
    │   ├── forms.py              # Form definitions
    │   ├── urls.py               # URL routing
    │   ├── templates/            # HTML templates
    │   │   ├── base.html
    │   │   ├── upload.html
    │   │   ├── documents.html
    │   │   └── jobs.html
    │   └── static/               # CSS, JS, images
    │       ├── css/
    │       ├── js/
    │       └── img/
    ├── api_client/               # Backend API client
    │   ├── __init__.py
    │   └── client.py             # HTTP client wrapper
    └── tests/
```

## Service Responsibilities

### Backend (FastAPI)

**Responsibilities:**
- Core business logic and domain models
- Data persistence and retrieval
- OCR processing (via Celery workers)
- RESTful API endpoints
- Authentication and authorization
- File storage management

**Technology Stack:**
- FastAPI for HTTP API
- SQLAlchemy for ORM
- Celery for async task processing
- PostgreSQL for data storage
- Redis for task queue
- Tesseract for OCR

**Does NOT:**
- Render HTML templates
- Handle user sessions (unless API requires auth)
- Serve static files

### Frontend (Django)

**Responsibilities:**
- User interface (HTML templates)
- Form handling and validation
- User sessions and cookies
- Static file serving
- Client-side logic coordination
- HTTP requests to backend API

**Technology Stack:**
- Django web framework
- Django templates for HTML
- httpx for API communication
- Bootstrap/Tailwind for styling
- gunicorn for WSGI server
- WhiteNoise for static files

**Does NOT:**
- Access database directly
- Perform OCR processing
- Contain business logic
- Store application data

## Dependency Management

### Backend pyproject.toml

**Location:** `backend/pyproject.toml`

```toml
[project]
name = "kul-ocr-backend"
version = "0.1.0"
description = "OCR Backend API Service"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "beartype>=0.22.5",
    "celery>=5.5.3",
    "celery-stubs>=0.1.3",
    "celery-types>=0.23.0",
    "fastapi[standard]>=0.121.3",
    "msgspec>=0.19.0",
    "pydantic-settings>=2.12.0",
    "pymupdf>=1.26.6",
    "pytesseract>=0.3.13",
    "sqlalchemy>=2.0.44",
    "structlog>=25.5.0",
    "psycopg2-binary>=2.9.9",
    "redis>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "basedpyright>=1.33.0",
    "detect-secrets>=1.5.0",
    "httpx>=0.28.1",
    "pre-commit>=4.5.0",
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
    "pytest-env>=1.2.0",
    "ruff>=0.14.6",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src"]
```

### Frontend pyproject.toml

**Location:** `frontend/pyproject.toml`

```toml
[project]
name = "kul-ocr-frontend"
version = "0.1.0"
description = "OCR Frontend Web Interface"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "django>=5.0.0",
    "django-environ>=0.11.2",
    "httpx>=0.28.1",
    "gunicorn>=22.0.0",
    "whitenoise>=6.7.0",
    "django-crispy-forms>=2.3",
    "crispy-bootstrap5>=2024.2",
]

[project.optional-dependencies]
dev = [
    "django-debug-toolbar>=4.4.0",
    "pytest>=9.0.0",
    "pytest-django>=4.8.0",
    "ruff>=0.14.6",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["frontend_app*", "web*", "api_client*"]

[tool.ruff]
line-length = 88
target-version = "py312"
```

### Root Workspace Configuration

**Location:** `pyproject.toml` (root)

```toml
[tool.uv.workspace]
members = ["backend", "frontend"]

[tool.uv]
dev-dependencies = [
    "pre-commit>=4.5.0",
    "ruff>=0.14.6",
]
```

This allows unified dependency management:

```bash
# Install all workspace dependencies
uv sync

# Run commands in specific packages
uv run --package kul-ocr-backend pytest
uv run --package kul-ocr-frontend python manage.py test
```

## Import Resolution

### Backend Imports

Backend imports work within the `kul_ocr` package:

```python
# backend/src/kul_ocr/entrypoints/api.py
from kul_ocr.domain import ports, model, exceptions
from kul_ocr.service_layer import services, uow
from kul_ocr.adapters.database import orm
```

The `PYTHONPATH` is set to `/app/src` in the Docker container, enabling proper import resolution.

### Frontend Imports

Frontend imports Django apps and local modules:

```python
# frontend/web/views.py
from django.shortcuts import render, redirect
from django.contrib import messages

# Local Django app imports
from api_client.client import api_client
from web.forms import DocumentUploadForm
```

**Important:** Frontend **NEVER** imports from backend. Communication happens via HTTP API.

## Docker Configuration

### Backend Dockerfile

**Location:** `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend project files
COPY backend/pyproject.toml backend/uv.lock* /app/

# Install uv and dependencies
RUN pip install uv && \
    uv sync --frozen --no-dev

# Copy backend source code
COPY backend/src /app/src

# Set Python path for import resolution
ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uv", "run", "fastapi", "dev", "kul_ocr.entrypoints.api:app", \
     "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

**Location:** `frontend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy frontend files
COPY frontend/pyproject.toml /app/
COPY frontend/ /app/

# Install dependencies
RUN pip install uv && \
    uv sync --frozen --no-dev

# Collect static files
RUN uv run python manage.py collectstatic --noinput

EXPOSE 8080

# Run with gunicorn (production)
CMD ["uv", "run", "gunicorn", "frontend_app.wsgi:application", \
     "--bind", "0.0.0.0:8080", "--workers", "4"]
```

### docker-compose.yaml

**Location:** `docker-compose.yaml` (root)

```yaml
version: '3.8'

services:
  # Backend API (FastAPI)
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: kul_ocr_backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://ocr_user:ocr_pass@db:5432/ocr_db
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./backend/src:/app/src      # Hot reload in development
      - ./storage:/app/storage
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - kul_network
    command: >
      uv run fastapi dev kul_ocr.entrypoints.api:app
      --host 0.0.0.0 --port 8000

  # Frontend Web UI (Django)
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: kul_ocr_frontend
    ports:
      - "8080:8080"
    environment:
      - BACKEND_API_URL=http://backend:8000
      - SECRET_KEY=${DJANGO_SECRET_KEY:-dev-secret-key-change-in-production}
      - DEBUG=True
    volumes:
      - ./frontend:/app              # Hot reload in development
    depends_on:
      - backend
    networks:
      - kul_network
    command: >
      uv run python manage.py runserver 0.0.0.0:8080

  # Celery Worker for OCR tasks
  celery_worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: kul_ocr_celery
    environment:
      - DATABASE_URL=postgresql://ocr_user:ocr_pass@db:5432/ocr_db
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    volumes:
      - ./backend/src:/app/src
      - ./storage:/app/storage
    depends_on:
      - db
      - redis
    networks:
      - kul_network
    command: >
      uv run celery -A kul_ocr.entrypoints.celery_app worker
      --loglevel=info

  # PostgreSQL Database
  db:
    image: postgres:16-alpine
    container_name: kul_ocr_db
    environment:
      POSTGRES_DB: ocr_db
      POSTGRES_USER: ocr_user
      POSTGRES_PASSWORD: ocr_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - kul_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ocr_user -d ocr_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis for Celery broker
  redis:
    image: redis:7-alpine
    container_name: kul_ocr_redis
    ports:
      - "6379:6379"
    networks:
      - kul_network

volumes:
  postgres_data:

networks:
  kul_network:
    driver: bridge
```

## Development Workflow

### Local Development (Without Docker)

**Backend Development:**

```bash
cd backend
uv sync
uv run fastapi dev src/kul_ocr/entrypoints/api.py
```

Backend will be available at: `http://localhost:8000`

**Frontend Development:**

```bash
cd frontend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 8080
```

Frontend will be available at: `http://localhost:8080`

### Docker Development

**Start all services:**

```bash
docker-compose up --build
```

**View logs:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Run commands in containers:**

```bash
# Backend tests
docker-compose exec backend uv run pytest

# Frontend migrations
docker-compose exec frontend uv run python manage.py migrate

# Create Django superuser
docker-compose exec frontend uv run python manage.py createsuperuser
```

**Stop services:**

```bash
docker-compose down

# Remove volumes (database data)
docker-compose down -v
```

## Communication Between Services

### API Client Pattern

The frontend communicates with the backend via a dedicated API client:

**Location:** `frontend/api_client/client.py`

```python
import httpx
from django.conf import settings
from typing import BinaryIO, Optional

class BackendAPIClient:
    """Client for communicating with FastAPI backend"""

    def __init__(self):
        self.base_url = settings.BACKEND_API_URL
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True
        )

    def upload_document(self, file: BinaryIO, filename: str) -> dict:
        """Upload document to backend API"""
        files = {'file': (filename, file)}
        response = self.client.post('/documents', files=files)
        response.raise_for_status()
        return response.json()

    def get_document(self, document_id: str) -> dict:
        """Get document details with OCR results"""
        response = self.client.get(f'/documents/{document_id}')
        response.raise_for_status()
        return response.json()

    def list_ocr_jobs(
        self,
        status: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> dict:
        """List OCR jobs with optional filters"""
        params = {}
        if status:
            params['status'] = status
        if document_id:
            params['document_id'] = document_id

        response = self.client.get('/ocr/jobs', params=params)
        response.raise_for_status()
        return response.json()

    def download_document(self, document_id: str) -> tuple[bytes, dict]:
        """Download document file from backend"""
        response = self.client.get(f'/documents/{document_id}/download')
        response.raise_for_status()
        return response.content, response.headers

    def close(self):
        """Close HTTP client connection"""
        self.client.close()

# Singleton instance
api_client = BackendAPIClient()
```

### Django Views Example

**Location:** `frontend/web/views.py`

```python
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from api_client.client import api_client
from web.forms import DocumentUploadForm

def upload_document(request):
    """Handle document upload form"""
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file = request.FILES['file']
                # Call backend API
                result = api_client.upload_document(file, file.name)
                messages.success(
                    request,
                    f"Document uploaded successfully: {result['id']}"
                )
                return redirect('document_detail', document_id=result['id'])
            except Exception as e:
                messages.error(request, f"Upload failed: {str(e)}")
    else:
        form = DocumentUploadForm()

    return render(request, 'web/upload.html', {'form': form})

def document_detail(request, document_id):
    """Display document details and OCR results"""
    try:
        # Call backend API
        document = api_client.get_document(document_id)
        return render(request, 'web/document_detail.html', {
            'document': document
        })
    except Exception as e:
        messages.error(request, f"Error loading document: {str(e)}")
        return redirect('upload_document')

def list_jobs(request):
    """List OCR jobs with optional filtering"""
    status = request.GET.get('status')
    document_id = request.GET.get('document_id')

    try:
        # Call backend API
        jobs_data = api_client.list_ocr_jobs(
            status=status,
            document_id=document_id
        )
        return render(request, 'web/jobs.html', {
            'jobs': jobs_data['jobs'],
            'total': jobs_data['total'],
            'status_filter': status
        })
    except Exception as e:
        messages.error(request, f"Error loading jobs: {str(e)}")
        return render(request, 'web/jobs.html', {
            'jobs': [],
            'total': 0
        })
```

## Environment Configuration

### Backend Environment Variables

**Location:** `.env` (or environment in docker-compose.yaml)

```bash
# Database
DATABASE_URL=postgresql://ocr_user:ocr_pass@localhost:5432/ocr_db

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage
STORAGE_PATH=./storage

# Logging
LOG_LEVEL=INFO
```

### Frontend Environment Variables

```bash
# Backend API
BACKEND_API_URL=http://localhost:8000

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,frontend

# Static files
STATIC_ROOT=/app/staticfiles
STATIC_URL=/static/
```

## Benefits of This Architecture

1. **Separation of Concerns**
   - Frontend handles presentation logic only
   - Backend handles business logic and data
   - Clear boundaries between layers

2. **Independent Scaling**
   - Scale frontend and backend independently
   - Add more backend workers for heavy OCR processing
   - Add more frontend instances for high traffic

3. **Technology Flexibility**
   - Easy to replace frontend (React, Vue, etc.)
   - Backend API can serve multiple clients (web, mobile, CLI)
   - Services can use different databases if needed

4. **Development Workflow**
   - Frontend and backend teams can work independently
   - Clear API contract between services
   - Easier testing and debugging

5. **Deployment Flexibility**
   - Deploy services to different servers
   - Use different hosting providers
   - Implement service-specific CI/CD pipelines

## API Contract

The backend exposes the following REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents` | Upload a new document |
| `GET` | `/documents/{id}` | Get document details with OCR results |
| `GET` | `/documents/{id}/download` | Download original document file |
| `GET` | `/ocr/jobs` | List OCR jobs (with filters) |

See the backend API documentation for detailed request/response schemas.

## Testing Strategy

### Backend Tests

```bash
cd backend
uv run pytest tests/
```

Tests focus on:
- Domain logic (unit tests)
- Service layer (integration tests)
- API endpoints (e2e tests)
- Repository layer (database tests)

### Frontend Tests

```bash
cd frontend
uv run pytest tests/
```

Tests focus on:
- View rendering (template tests)
- Form validation (form tests)
- API client mocking (unit tests)
- User workflows (integration tests)

## Troubleshooting

### Common Issues

**Frontend cannot connect to backend:**
- Check `BACKEND_API_URL` environment variable
- Ensure backend container is running: `docker-compose ps`
- Verify network connectivity: `docker-compose exec frontend ping backend`

**Import errors in backend:**
- Verify `PYTHONPATH` is set correctly in Dockerfile
- Check package structure in `backend/src/`
- Ensure `uv sync` has been run

**Static files not loading:**
- Run `python manage.py collectstatic` in frontend
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify WhiteNoise middleware is configured

**Database connection failed:**
- Wait for database to be healthy: check healthcheck in docker-compose
- Verify `DATABASE_URL` matches docker-compose settings
- Check PostgreSQL logs: `docker-compose logs db`

## Next Steps

- [Installation Guide](INSTALLATION.md) - Set up the development environment
- [Contributing](CONTRIBUTING.md) - How to contribute to the project
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions (TODO)
