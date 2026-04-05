"""Jobs router: ingest, list, and retrieve job postings."""

from __future__ import annotations

import json
from typing import Any, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job
from app.schemas import IngestJobsRequest, IngestJobsResponse, JobListResponse, JobRead
from app.services import extractor, fetcher, parser

router = APIRouter()


def _is_valid_http_url(url: str) -> bool:
    """Return True when the URL uses http/https and has a network location."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _build_job_from_parsed(url: str, parsed_data: dict[str, Any]) -> Job:
    """Create a Job ORM object from parsed page data."""
    raw_description = parsed_data.get("description_raw", "") or ""
    cleaned_description = extractor.clean_text(raw_description)
    skills = extractor.extract_skills(cleaned_description)

    return Job(
        url=url,
        source=parsed_data.get("source"),
        title=parsed_data.get("title"),
        company=parsed_data.get("company"),
        location=parsed_data.get("location"),
        employment_type=parsed_data.get("employment_type"),
        date_posted=parsed_data.get("date_posted"),
        job_type=parsed_data.get("job_type"),
        description_raw=raw_description,
        description_clean=cleaned_description,
        skills_json=json.dumps(skills),
    )


@router.post("/ingest", response_model=IngestJobsResponse)
async def ingest_jobs(
    request: IngestJobsRequest,
    session: Session = Depends(get_session),
) -> IngestJobsResponse:
    """Fetch, parse, and store job postings from the provided URLs.

    Existing URLs are returned without re-fetching. Invalid or failed URLs are
    reported in the response instead of failing the whole batch.
    """
    saved_jobs: List[Job] = []
    failures: list[dict[str, str]] = []
    ingested_count = 0
    existing_count = 0

    for url in request.urls:
        if not _is_valid_http_url(url):
            failures.append({"url": url, "error": "Invalid URL. Only http/https URLs are allowed."})
            continue

        existing = session.exec(select(Job).where(Job.url == url)).first()
        if existing:
            saved_jobs.append(existing)
            existing_count += 1
            continue

        try:
            html = await fetcher.fetch_html(url)
            parsed_data = parser.parse_job_page(url, html)
            print(json.dumps(parsed_data, indent=2))
            job = _build_job_from_parsed(url, parsed_data)

            session.add(job)
            session.commit()
            session.refresh(job)

            saved_jobs.append(job)
            ingested_count += 1

        except Exception as exc:
            session.rollback()
            failures.append({"url": url, "error": str(exc)})

    return IngestJobsResponse(
        ingested_count=ingested_count,
        existing_count=existing_count,
        failed_count=len(failures),
        jobs=[JobRead.model_validate(job) for job in saved_jobs],
        failures=failures,
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    keyword: Optional[str] = Query(default=None),
    company: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> JobListResponse:
    """Return a filtered list of job postings."""
    jobs = session.exec(select(Job)).all()

    keyword_normalized = keyword.lower().strip() if keyword else None
    company_normalized = company.lower().strip() if company else None
    location_normalized = location.lower().strip() if location else None

    results: list[Job] = []
    for job in jobs:
        job_company = (job.company or "").lower().strip()
        job_location = (job.location or "").lower().strip()
        haystack = " ".join(
            part for part in [job.title, job.description_clean, job.description_raw] if part
        ).lower()

        if company_normalized and company_normalized != job_company:
            continue
        if location_normalized and location_normalized != job_location:
            continue
        if keyword_normalized and keyword_normalized not in haystack:
            continue

        results.append(job)

    return JobListResponse(
        total=len(results),
        jobs=[JobRead.model_validate(job) for job in results],
    )


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, session: Session = Depends(get_session)) -> JobRead:
    """Return a single job posting by ID."""
    job = session.get(Job, job_id)
    if not job:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job not found")

    return JobRead.model_validate(job)