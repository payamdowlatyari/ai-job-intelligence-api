"""Routes for cover letter generation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job
from app.schemas import (
    CoverLetterRequest,
    CoverLetterFromUrlRequest,
    CoverLetterResponse,
)
from app.services.cover_letter_service import generate_cover_letter
from app.services.embedding_service import build_job_text

# Adjust this import to your actual ingestion function
from app.services.job_ingestion_service import ingest_job_from_url

router = APIRouter()

@router.post("/cover-letter", response_model=CoverLetterResponse)
def create_cover_letter(
    payload: CoverLetterRequest,
    session: Session = Depends(get_session),
) -> CoverLetterResponse:
    job = None
    job_text = payload.job_text
    company = payload.company_override
    role_title = None
    job_url = None

    if payload.job_id is not None:
        job = session.get(Job, payload.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        job_text = build_job_text(job)
        company = company or job.company
        role_title = job.title
        job_url = job.url

    if not job_text or not job_text.strip():
        raise HTTPException(status_code=400, detail="Job text is empty")

    try:
        cover_letter = generate_cover_letter(
            resume_text=payload.resume_text,
            job_text=job_text,
            candidate_name=payload.candidate_name,
            company=company,
            role_title=role_title,
            tone=payload.tone,
            length=payload.length,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cover letter generation failed: {exc}")

    return CoverLetterResponse(
        job_id=job.id if job else None,
        job_url=job_url,
        company=company,
        role_title=role_title,
        cover_letter=cover_letter,
        was_job_created=False,
    )


@router.post("/cover-letter/from-url", response_model=CoverLetterResponse)
def create_cover_letter_from_url(
    payload: CoverLetterFromUrlRequest,
    session: Session = Depends(get_session),
) -> CoverLetterResponse:
    job_url = str(payload.job_url)

    existing_job = session.exec(
        select(Job).where(Job.url == job_url)
    ).first()

    was_job_created = False

    if existing_job:
        job = existing_job
    else:
        try:
            job = ingest_job_from_url(job_url=job_url, session=session)
            was_job_created = True
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to ingest job from URL: {exc}")

    job_text = build_job_text(job)
    if not job_text:
        raise HTTPException(status_code=400, detail="Stored job has no usable text")

    try:
        cover_letter = generate_cover_letter(
            resume_text=payload.resume_text,
            job_text=job_text,
            candidate_name=payload.candidate_name,
            company=job.company,
            role_title=job.title,
            tone=payload.tone,
            length=payload.length,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cover letter generation failed: {exc}")

    return CoverLetterResponse(
        job_id=job.id,
        job_url=job.url,
        company=job.company,
        role_title=job.title,
        cover_letter=cover_letter,
        was_job_created=was_job_created,
    )