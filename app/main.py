"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import ROOT_PATH, API_VERSION
from app.routes import jobs, summarize, match, cover_letter


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="AI Job Intelligence API",
    description="Fetch, parse, store and analyze job postings with AI-ready endpoints.",
    version=API_VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path=ROOT_PATH,
    openapi_tags=[
        {"name": "general", "description": "General endpoints including health-check"},
        {"name": "jobs", "description": "Job postings"},
    ],
    contact={
        "name": "AI Job Intelligence",
        "url": "https://github.com/ai-job-intelligence/ai-job-intelligence-api",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["general"])
def root() -> dict:
    """Return a simple health-check response."""
    return {
        "status": "ok",
        "message": "Welcome to the AI Job Intelligence API! 🚀",
        "version": API_VERSION,
        "root_path": ROOT_PATH,
    }

@app.get("/health", tags=["general"])
def health_check() -> dict:
    """Return a simple health-check response."""
    return {
        "status": "ok",
        "message": "AI Job Intelligence API is healthy and running! ✅",
    }


app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(summarize.router, prefix="/jobs", tags=["jobs"])
app.include_router(match.router, prefix="/jobs", tags=["jobs"])
app.include_router(cover_letter.router, prefix="/jobs", tags=["jobs"])
