"""Jobs router: ingest, list, and retrieve job postings."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job
from app.schemas import IngestJobsRequest, IngestJobsResponse, JobListResponse, JobRead
from app.services import fetcher, parser, extractor

router = APIRouter()


@router.post("/ingest", response_model=IngestJobsResponse)
async def ingest_jobs(
    request: IngestJobsRequest,
    session: Session = Depends(get_session),
) -> IngestJobsResponse:
    """Fetch and parse job postings from the provided URLs, then store in the database.

    If a URL already exists in the database the existing record is returned without
    re-fetching.
    """
    saved: List[Job] = []

    for url in request.urls:
        # Return existing record if URL is already stored
        existing = session.exec(select(Job).where(Job.url == url)).first()
        if existing:
            saved.append(existing)
            continue

        # Fetch and parse
        try:
            html = await fetcher.fetch_html(url)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch {url}: {exc}")

        parsed = parser.parse_job_page(url, html)

        # Clean and extract skills from the raw description
        raw_description = parsed.get("description_raw", "") or ""
        clean = extractor.clean_text(raw_description)
        skills = extractor.extract_skills(clean)

        job = Job(
            url=url,
            source=parsed.get("source"),
            title=parsed.get("title"),
            company=parsed.get("company"),
            location=parsed.get("location"),
            description_raw=raw_description,
            description_clean=clean,
            skills_json=json.dumps(skills),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        saved.append(job)

    return IngestJobsResponse(count=len(saved), jobs=[JobRead.model_validate(j) for j in saved])


@router.get("", response_model=JobListResponse)
def list_jobs(
    keyword: Optional[str] = Query(default=None),
    company: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> JobListResponse:
    """Return a filtered list of job postings.

    Supports optional filtering by keyword (matched against title and description),
    company name, and location.
    """
    statement = select(Job)
    jobs = session.exec(statement).all()

    # Apply in-memory filters (suitable for a lightweight starter project)
    results = []
    for job in jobs:
        if company and (job.company or "").lower() != company.lower():
            continue
        if location and (job.location or "").lower() != location.lower():
            continue
        if keyword:
            kw = keyword.lower()
            haystack = " ".join(
                filter(None, [job.title, job.description_clean, job.description_raw])
            ).lower()
            if kw not in haystack:
                continue
        results.append(job)

    return JobListResponse(total=len(results), jobs=[JobRead.model_validate(j) for j in results])


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, session: Session = Depends(get_session)) -> JobRead:
    """Return a single job posting by ID, or 404 if not found."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)
