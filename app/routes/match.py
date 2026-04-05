"""Match router: score a candidate against a stored job posting."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.models import Job
from app.schemas import MatchRequest, MatchResponse
from app.services.extractor import extract_skills
from app.services.matcher import match_job
from app.utils.json import parse_skills_json

router = APIRouter()


def _merge_candidate_skills(
    explicit_skills: Optional[list[str]] = None,
    resume_text: Optional[str] = None,
) -> list[str]:
    """Merge explicit skills with skills extracted from resume text."""
    merged: list[str] = []

    if explicit_skills:
        merged.extend(skill.strip() for skill in explicit_skills if skill and skill.strip())

    if resume_text and resume_text.strip():
        merged.extend(extract_skills(resume_text))

    # Deduplicate while preserving order, case-insensitive
    seen: set[str] = set()
    normalized: list[str] = []
    for skill in merged:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(skill)

    return normalized


@router.post("/{job_id}/match", response_model=MatchResponse)
def match_job_route(
    job_id: int,
    request: MatchRequest,
    session: Session = Depends(get_session),
) -> MatchResponse:
    """Compare candidate skills or resume text against a stored job posting."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_skills = parse_skills_json(job.skills_json)
    candidate_skills = _merge_candidate_skills(request.skills, request.resume_text)

    result = match_job(job_skills, candidate_skills)

    return MatchResponse(
        job_id=job_id,
        fit_score=result["fit_score"],
        candidate_skills=result["candidate_skills"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        extra_candidate_skills=result["extra_candidate_skills"],
        notes=result["notes"],
    )