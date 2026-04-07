# app/services/job_ingestion_service.py

from sqlmodel import Session, select
from app.models import Job
from app.services.parser import parse_job_page


def ingest_job_from_url(job_url: str, session: Session) -> Job:
    """Fetch, parse, and store a job if it doesn't already exist."""

    # ✅ Check if already exists
    existing = session.exec(
        select(Job).where(Job.url == job_url)
    ).first()

    if existing:
        return existing

    # ✅ Use YOUR parser
    parsed = parse_job_page(job_url)

    # ⚠️ Important: adapt keys based on your parser output
    job = Job(
        url=job_url,
        source=parsed.get("source"),
        title=parsed.get("title"),
        company=parsed.get("company"),
        location=parsed.get("location"),
        description_raw=parsed.get("description_raw"),
        date_posted=parsed.get("date_posted"),
        job_type=parsed.get("job_type"),
    )

    try:
        session.add(job)
        session.commit()
        session.refresh(job)
    except Exception:
        session.rollback()
        raise

    return job