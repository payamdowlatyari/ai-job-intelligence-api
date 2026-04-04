"""Summarize router: generate a placeholder summary for a stored job."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Job
from app.schemas import SummarizeResponse
from app.services.summarizer import generate_placeholder_summary

router = APIRouter()


@router.post("/{job_id}/summarize", response_model=SummarizeResponse)
def summarize_job(job_id: int, session: Session = Depends(get_session)) -> SummarizeResponse:
    """Generate a heuristic-based placeholder summary for the given job and persist it."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = generate_placeholder_summary(job)

    # Persist the generated summary text
    job.summary = result["summary"]
    session.add(job)
    session.commit()

    return SummarizeResponse(
        job_id=job_id,
        summary=result["summary"],
        responsibilities=result["responsibilities"],
        required_skills=result["required_skills"],
        nice_to_have=result["nice_to_have"],
    )
