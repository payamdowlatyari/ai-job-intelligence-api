"""Service for generating placeholder summaries from stored job data."""

import json
from typing import Any, Dict, List

from app.models import Job


def _split_sentences(text: str) -> List[str]:
    """Naively split text into sentences on period / exclamation / question marks."""
    import re

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def generate_placeholder_summary(job: Job) -> Dict[str, Any]:
    """Produce a heuristic placeholder summary for a job posting.

    This function uses simple text heuristics and does *not* call any external
    AI/LLM API.  It is designed to be replaced with a real LLM integration later.
    Args:
        job: The Job ORM object retrieved from the database.

    Returns:
        A dictionary with keys: summary, responsibilities, required_skills, nice_to_have.
    """
    title = job.title or "this role"
    company = job.company or "the company"
    location = job.location or "an unspecified location"

    # Build a simple one-liner summary
    summary = f"{title} at {company} ({location})."

    # Extract skills already stored on the job
    skills: List[str] = json.loads(job.skills_json) if job.skills_json else []

    # Split the clean description into sentences for heuristic bucketing
    description = job.description_clean or job.description_raw or ""
    sentences = _split_sentences(description)

    # Heuristic: sentences containing action verbs are likely responsibilities
    responsibility_keywords = {"develop", "build", "design", "implement", "manage", "lead", "maintain", "create", "ensure", "drive"}
    responsibilities: List[str] = []
    for sentence in sentences[:20]:  # cap to first 20 sentences for brevity
        lower = sentence.lower()
        if any(kw in lower for kw in responsibility_keywords):
            responsibilities.append(sentence)
        if len(responsibilities) >= 5:
            break

    if not responsibilities and sentences:
        responsibilities = sentences[:3]

    # Split skills into required vs nice-to-have using a simple heuristic:
    # first half → required, second half → nice-to-have
    mid = max(1, len(skills) // 2)
    required_skills = skills[:mid]
    nice_to_have = skills[mid:]

    return {
        "summary": summary,
        "responsibilities": responsibilities,
        "required_skills": required_skills,
        "nice_to_have": nice_to_have,
    }
