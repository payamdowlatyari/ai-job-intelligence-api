"""Match router: score a candidate against a stored job posting."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Job
from app.schemas import MatchRequest, MatchResponse
from app.services.extractor import extract_skills
from app.services.matcher import match_job

router = APIRouter()


@router.post("/{job_id}/match", response_model=MatchResponse)
def match_job_route(
    job_id: int,
    request: MatchRequest,
    session: Session = Depends(get_session),
) -> MatchResponse:
    """Compare candidate skills (or resume text) against extracted job skills.

    Returns a fit score, matched skills, missing skills, and a short note.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Derive job skills from stored JSON
    job_skills: list[str] = json.loads(job.skills_json) if job.skills_json else []

    # Derive candidate skills from either explicit list or free-form resume text
    candidate_skills: list[str] = []
    if request.skills:
        candidate_skills = request.skills
    elif request.resume_text:
        candidate_skills = extract_skills(request.resume_text)

    result = match_job(job_skills, candidate_skills)

    return MatchResponse(
        fit_score=result["fit_score"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        notes=result["notes"],
    )
