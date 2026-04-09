"""Routes for AI-based job matching."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job
from app.schemas import JobRead, MatchRequest, MatchResponse, MatchResult, SkillMatchResponse
from app.services.embedding_service import (
    build_job_text,
    cosine_similarity,
    dumps_embedding,
    get_embedding,
    get_embeddings_batched,
    loads_embedding,
)
from app.services.extractor import extract_skills
from app.services.matcher import match_job
from app.utils.json import parse_skills_json

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_UNCACHED_JOB_EMBEDS_PER_REQUEST = 25


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

    seen: set[str] = set()
    normalized: list[str] = []
    for skill in merged:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(skill)

    return normalized


@router.post("/match", response_model=MatchResponse)
def match_jobs(
    payload: MatchRequest,
    session: Session = Depends(get_session),
) -> MatchResponse:
    """Match jobs to a resume."""

    query_text = payload.to_query_text()
    if not query_text:
        raise HTTPException(status_code=400, detail="No valid matching input provided.")

    try:
        candidate_embedding = get_embedding(query_text, use_local_cache=True)
    except Exception as exc:
        logger.error("Embedding service error: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Embedding service unavailable. Please try again later.")

    if not candidate_embedding:
        raise HTTPException(status_code=400, detail="Could not create embedding from input.")

    query = select(Job)

    if payload.location:
        query = query.where(Job.location.ilike(f"%{payload.location}%"))

    if payload.company:
        query = query.where(Job.company.ilike(f"%{payload.company}%"))

    if payload.job_type:
        query = query.where(Job.job_type.ilike(f"%{payload.job_type}%"))

    jobs = session.exec(query).all()

    cached_jobs: list[tuple[Job, list[float]]] = []
    uncached_jobs: list[tuple[Job, str]] = []

    for job in jobs:
        vector = loads_embedding(job.embedding_json)
        if vector:
            cached_jobs.append((job, vector))
            continue

        job_text = build_job_text(job)
        if job_text:
            uncached_jobs.append((job, job_text))

    # Protect the endpoint from runaway cost / quota usage
    uncached_jobs = uncached_jobs[:MAX_UNCACHED_JOB_EMBEDS_PER_REQUEST]

    if uncached_jobs:
        try:
            uncached_vectors = get_embeddings_batched([text for _, text in uncached_jobs])
        except Exception as exc:
            logger.error("Embedding service error: %s", exc, exc_info=True)
            raise HTTPException(status_code=503, detail="Embedding service unavailable. Please try again later.")

        if len(uncached_vectors) != len(uncached_jobs):
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Embedding service returned {len(uncached_vectors)} vectors "
                    f"but expected {len(uncached_jobs)}."
                ),
            )

        for (job, _), vector in zip(uncached_jobs, uncached_vectors):
            job.embedding_json = dumps_embedding(vector)
            session.add(job)
            cached_jobs.append((job, vector))

        session.commit()

    scored_matches: list[MatchResult] = []

    for job, vector in cached_jobs:
        score = cosine_similarity(candidate_embedding, vector)
        scored_matches.append(
            MatchResult(
                similarity_score=round(score, 4),
                match_reason=None,
                job=JobRead.model_validate(job),
            )
        )

    scored_matches.sort(key=lambda item: item.similarity_score, reverse=True)
    top_matches = scored_matches[: payload.top_k]

    return MatchResponse(
        total_candidates=len(scored_matches),
        matches=top_matches,
    )


@router.post(
    "/{job_id}/match",
    response_model=SkillMatchResponse,
    deprecated=True,
    summary="Match candidate to a single job (deprecated)",
)
def match_job_route(
    job_id: int,
    request: MatchRequest,
    session: Session = Depends(get_session),
) -> SkillMatchResponse:
    """Compare candidate skills or resume text against a stored job posting.

    .. deprecated::
        Use ``POST /jobs/match`` for semantic embedding-based matching across
        all jobs.  This endpoint is kept for backward compatibility only.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        job_skills = parse_skills_json(job.skills_json)
        candidate_skills = _merge_candidate_skills(request.skills, request.resume_text)
    except Exception as exc:
        logger.error("Skill extraction error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process skills. Please try again.")

    result = match_job(job_skills, candidate_skills)

    return SkillMatchResponse(
        job_id=job_id,
        fit_score=result["fit_score"],
        candidate_skills=result["candidate_skills"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        extra_candidate_skills=result["extra_candidate_skills"],
        notes=result["notes"],
    )