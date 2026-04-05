"""Pydantic / SQLModel schemas for request and response validation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, model_validator


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
    date_posted: Optional[str] = None
    job_type: Optional[str] = None
    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Schema for a paginated/filtered list of jobs."""

    total: int
    jobs: List[JobRead]


class IngestJobsRequest(BaseModel):
    """Schema for the job ingestion request."""

    urls: List[str]


class IngestFailure(BaseModel):
    """Schema for a failed job ingestion."""

    url: str
    error: str


class IngestJobsResponse(BaseModel):
    """Schema for the job ingestion response."""

    ingested_count: int
    existing_count: int
    failed_count: int
    jobs: List[JobRead]
    failures: List[IngestFailure]


class MatchRequest(BaseModel):
    """Schema for the job match request."""

    resume_text: Optional[str] = None
    skills: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_input(self) -> "MatchRequest":
        """Require at least one non-empty input source."""
        has_resume = bool(self.resume_text and self.resume_text.strip())
        has_skills = bool(self.skills and any(skill.strip() for skill in self.skills if skill))

        if not has_resume and not has_skills:
            raise ValueError("Provide either resume_text or skills.")
        return self


class MatchResponse(BaseModel):
    """Schema for the job match response."""

    job_id: int
    fit_score: int
    candidate_skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    extra_candidate_skills: List[str]
    notes: str


class SummarizeResponse(BaseModel):
    """Schema for the summarize response."""

    job_id: int
    summary: str
    seniority: str
    responsibilities: List[str]
    required_skills: List[str]
    nice_to_have: List[str]