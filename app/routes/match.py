"""Routes for AI-based job matching."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job
from app.schemas import JobRead, MatchRequest, MatchResponse, MatchResult
from app.services.embedding_service import (
    build_job_text,
    cosine_similarity,
    dumps_embedding,
    get_embedding,
    get_embeddings_batched,
    loads_embedding,
)

router = APIRouter()

MAX_UNCACHED_JOB_EMBEDS_PER_REQUEST = 25


@router.post("/match", response_model=MatchResponse)
def match_jobs(
    payload: MatchRequest,
    session: Session = Depends(get_session),
) -> MatchResponse:
    query_text = payload.to_query_text()
    if not query_text:
        raise HTTPException(status_code=400, detail="No valid matching input provided.")

    try:
        candidate_embedding = get_embedding(query_text, use_local_cache=True)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {exc}")

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
            raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {exc}")

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