"""SQLModel table definition for the Job entity."""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    """Represents a job posting stored in the database."""

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    source: Optional[str] = Field(default=None, index=True)
    title: Optional[str] = Field(default=None, index=True)
    company: Optional[str] = Field(default=None, index=True)
    location: Optional[str] = Field(default=None, index=True)
    employment_type: Optional[str] = None
    description_raw: Optional[str] = None
    description_clean: Optional[str] = None
    skills_json: Optional[str] = None
    summary: Optional[str] = None
    date_posted: Optional[str] = Field(default=None)
    job_type: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    