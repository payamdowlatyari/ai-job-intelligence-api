"""Pydantic / SQLModel schemas for request and response validation."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class JobCreate(BaseModel):
    """Schema for creating a new job record."""

    url: str
    source: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description_raw: Optional[str] = None
    description_clean: Optional[str] = None
    skills_json: Optional[str] = None


class JobRead(BaseModel):
    """Schema for reading a job record from the database."""

    id: int
    url: str
    source: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description_raw: Optional[str] = None
    description_clean: Optional[str] = None
    skills_json: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Schema for a paginated/filtered list of jobs."""

    total: int
    jobs: List[JobRead]


class IngestJobsRequest(BaseModel):
    """Schema for the job ingestion request."""

    urls: List[str]


class IngestJobsResponse(BaseModel):
    """Schema for the job ingestion response."""

    count: int
    jobs: List[JobRead]


class MatchRequest(BaseModel):
    """Schema for the job match request."""

    resume_text: Optional[str] = None
    skills: Optional[List[str]] = None


class MatchResponse(BaseModel):
    """Schema for the job match response."""

    fit_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    notes: str


class SummarizeResponse(BaseModel):
    """Schema for the summarize response."""

    job_id: int
    summary: str
    responsibilities: List[str]
    required_skills: List[str]
    nice_to_have: List[str]
