"""Service for computing a skill-overlap match score between a job and a candidate."""

from typing import Any


def _normalize_skills(skills: list[str]) -> list[str]:
    """Normalize skills by trimming, deduplicating, and preserving first-seen casing."""
    seen: set[str] = set()
    normalized: list[str] = []

    for skill in skills:
        cleaned = skill.strip()
        if not cleaned:
            continue

        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(cleaned)

    return normalized


def match_job(job_skills: list[str], candidate_skills: list[str]) -> dict[str, Any]:
    """Compute a deterministic overlap-based fit score.

    Args:
        job_skills: Skills extracted from the job posting.
        candidate_skills: Skills provided directly or extracted from resume text.

    Returns:
        A dictionary containing score, overlap details, and a short note.
    """
    normalized_job = _normalize_skills(job_skills)
    normalized_candidate = _normalize_skills(candidate_skills)

    job_map = {skill.lower(): skill for skill in normalized_job}
    candidate_map = {skill.lower(): skill for skill in normalized_candidate}

    job_keys = set(job_map.keys())
    candidate_keys = set(candidate_map.keys())

    if not job_keys:
        return {
            "fit_score": 0,
            "candidate_skills": normalized_candidate,
            "matched_skills": [],
            "missing_skills": [],
            "extra_candidate_skills": normalized_candidate,
            "notes": "No extracted job skills were available, so this score has low confidence.",
        }

    matched_keys = job_keys & candidate_keys
    missing_keys = job_keys - candidate_keys
    extra_keys = candidate_keys - job_keys

    matched_skills = sorted((job_map[key] for key in matched_keys), key=str.lower)
    missing_skills = sorted((job_map[key] for key in missing_keys), key=str.lower)
    extra_candidate_skills = sorted(
        (candidate_map[key] for key in extra_keys),
        key=str.lower,
    )

    overlap_ratio = len(matched_keys) / len(job_keys)
    fit_score = round(overlap_ratio * 100)

    if fit_score >= 80:
        notes = "Strong match — most extracted job skills are covered."
    elif fit_score >= 50:
        notes = "Moderate match — several relevant skills are present, but there are still gaps."
    elif fit_score > 0:
        notes = "Partial match — some overlap exists, but important skills are missing."
    else:
        notes = "Low match — no meaningful skill overlap was found."

    return {
        "fit_score": fit_score,
        "candidate_skills": normalized_candidate,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "extra_candidate_skills": extra_candidate_skills,
        "notes": notes,
    }