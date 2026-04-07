"""Pydantic / SQLModel schemas for request and response validation."""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, HttpUrl, Field, model_validator


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
    date_posted: Optional[str] = None
    job_type: Optional[str] = None


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
    """Schema for semantic job matching request."""

    resume_text: Optional[str] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    company: Optional[str] = None
    job_type: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_input(self) -> "MatchRequest":
        """Require at least one non-empty input source."""
        has_resume = bool(self.resume_text and self.resume_text.strip())
        has_skills = bool(
            self.skills and any(skill and skill.strip() for skill in self.skills)
        )

        if not has_resume and not has_skills:
            raise ValueError("Provide either resume_text or skills.")

        return self

    def to_query_text(self) -> str:
        """Build a single text block for embedding-based matching."""
        parts: List[str] = []

        if self.resume_text and self.resume_text.strip():
            parts.append(self.resume_text.strip())

        if self.skills:
            cleaned_skills = [skill.strip() for skill in self.skills if skill and skill.strip()]
            if cleaned_skills:
                parts.append("Skills: " + ", ".join(cleaned_skills))

        return "\n\n".join(parts).strip()


class MatchResult(BaseModel):
    """Schema for a single matched job."""

    similarity_score: float
    match_reason: Optional[str] = None
    job: JobRead


class MatchResponse(BaseModel):
    """Schema for semantic job match response."""

    total_candidates: int
    matches: List[MatchResult]


class SkillMatchResponse(BaseModel):
    """Schema for the legacy skill-overlap job match response (POST /jobs/{job_id}/match)."""

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


class CoverLetterRequest(BaseModel):
    """Generate a cover letter from an existing job or raw job text."""

    job_id: Optional[int] = None
    job_text: Optional[str] = None
    resume_text: str
    candidate_name: Optional[str] = None
    company_override: Optional[str] = None
    tone: Literal["professional", "warm", "confident"] = "professional"
    length: Literal["short", "medium", "long"] = "medium"

    @model_validator(mode="after")
    def validate_job_source(self) -> "CoverLetterRequest":
        has_job_id = self.job_id is not None
        has_job_text = bool(self.job_text and self.job_text.strip())

        if not has_job_id and not has_job_text:
            raise ValueError("Provide either job_id or job_text.")

        return self


class CoverLetterFromUrlRequest(BaseModel):
    """Generate a cover letter from a job URL, ingesting the job if needed."""

    job_url: HttpUrl
    resume_text: str
    candidate_name: Optional[str] = None
    tone: Literal["professional", "warm", "confident"] = "professional"
    length: Literal["short", "medium", "long"] = "medium"


class CoverLetterResponse(BaseModel):
    """Generated cover letter response."""

    job_id: Optional[int] = None
    job_url: Optional[str] = None
    company: Optional[str] = None
    role_title: Optional[str] = None
    cover_letter: str
    was_job_created: bool = False