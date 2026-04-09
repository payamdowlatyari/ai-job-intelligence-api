# app/services/job_ingestion_service.py

import json

from sqlmodel import Session, select

from app.models import Job
from app.services import extractor, fetcher, parser


async def ingest_job_from_url(job_url: str, session: Session) -> Job:
    """Fetch, parse, and store a job if it doesn't already exist."""

    existing = session.exec(
        select(Job).where(Job.url == job_url)
    ).first()

    if existing:
        return existing

    html = await fetcher.fetch_html(job_url)
    parsed = parser.parse_job_page(job_url, html)

    raw_description = parsed.get("description_raw", "") or ""
    cleaned_description = extractor.clean_text(raw_description)
    skills = extractor.extract_skills(cleaned_description)

    job = Job(
        url=job_url,
        source=parsed.get("source"),
        title=parsed.get("title"),
        company=parsed.get("company"),
        location=parsed.get("location"),
        employment_type=parsed.get("employment_type"),
        date_posted=parsed.get("date_posted"),
        job_type=parsed.get("job_type"),
        description_raw=raw_description,
        description_clean=cleaned_description,
        skills_json=json.dumps(skills),
    )

    try:
        session.add(job)
        session.commit()
        session.refresh(job)
    except Exception:
        session.rollback()
        raise

    return job