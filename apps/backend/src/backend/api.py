from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.documents.views import router as documents_router
from backend.jobs.views import router as jobs_router

from core.adapters.database import orm

from backend import exception_handlers

_ = load_dotenv()

orm.start_mappers()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/ocr/jobs", tags=["jobs"])
app.include_router(documents_router, prefix="/documents", tags=["documents"])

exception_handlers.register_handlers(app)
