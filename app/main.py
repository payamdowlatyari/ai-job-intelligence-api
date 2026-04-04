"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.db import create_db_and_tables
from app.routes import jobs, summarize, match


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create database tables on startup."""
    create_db_and_tables()
    yield


app = FastAPI(
    title="AI Job Intelligence API",
    description="Fetch, parse, store and analyze job postings with AI-ready endpoints.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Return a simple health-check response."""
    return {"status": "ok"}


app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(summarize.router, prefix="/jobs", tags=["summarize"])
app.include_router(match.router, prefix="/jobs", tags=["match"])
