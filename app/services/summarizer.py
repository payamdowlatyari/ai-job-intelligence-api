"""Service for generating a deterministic summary for a job posting."""

from __future__ import annotations

import re
from typing import Any

from app.models import Job
from app.utils.json import parse_skills_json


SENIORITY_RULES = [
    ("staff", "Staff"),
    ("principal", "Principal"),
    ("lead", "Lead"),
    ("senior", "Senior"),
    ("sr", "Senior"),
    ("mid", "Mid-level"),
    ("ii", "Mid-level"),
    ("iii", "Senior"),
    ("junior", "Junior"),
    ("jr", "Junior"),
    ("intern", "Intern"),
]


RESPONSIBILITY_PATTERNS = [
    r"\bbuild\b",
    r"\bdesign\b",
    r"\bdevelop\b",
    r"\bimplement\b",
    r"\bmaintain\b",
    r"\boptimi[sz]e\b",
    r"\bcollaborate\b",
    r"\bsupport\b",
    r"\bown\b",
    r"\bdeliver\b",
    r"\bscale\b",
    r"\bimprove\b",
]


NICE_TO_HAVE_HINTS = [
    "nice to have",
    "preferred",
    "bonus",
    "plus",
    "good to have",
]


def _infer_seniority(title: str | None) -> str:
    """Infer seniority from job title."""
    if not title:
        return "Unknown"

    lowered = title.lower()
    for token, label in SENIORITY_RULES:
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            return label

    return "Not specified"


def _split_sentences(text: str) -> list[str]:
    """Split text into rough sentences."""
    if not text:
        return []

    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" -•\t") for part in parts if part.strip()]


def _extract_responsibilities(description: str | None, limit: int = 4) -> list[str]:
    """Extract likely responsibility statements from the description."""
    if not description:
        return []

    sentences = _split_sentences(description)
    selected: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        if any(re.search(pattern, lowered) for pattern in RESPONSIBILITY_PATTERNS):
            cleaned = sentence.strip()
            if len(cleaned) > 20 and cleaned not in selected:
                selected.append(cleaned)

        if len(selected) >= limit:
            break

    return selected


def _classify_skills(description: str | None, skills: list[str]) -> tuple[list[str], list[str]]:
    """Split extracted skills into required and nice-to-have groups."""
    if not skills:
        return [], []

    description_lower = (description or "").lower()

    required_skills: list[str] = []
    nice_to_have: list[str] = []

    for skill in skills:
        skill_lower = skill.lower()

        if any(hint in description_lower for hint in NICE_TO_HAVE_HINTS):
            # Light heuristic:
            # if the skill appears near a nice-to-have phrase, classify as optional
            match = re.search(
                rf"(.{{0,80}}(?:{'|'.join(map(re.escape, NICE_TO_HAVE_HINTS))}).{{0,80}}{re.escape(skill_lower)})",
                description_lower,
            )
            if match:
                nice_to_have.append(skill)
                continue

        required_skills.append(skill)

    return required_skills, nice_to_have


def _build_summary(
    title: str | None,
    company: str | None,
    location: str | None,
    seniority: str,
    required_skills: list[str],
) -> str:
    """Build a concise summary paragraph.

    Args:
        title: The job title.
        company: The company name.
        location: The job location.
        seniority: The inferred seniority level.
        required_skills: A list of required skills.

    Returns:
        A concise summary paragraph.
    """
    role = title or "This role"
    company_part = f" at {company}" if company else ""
    location_part = f" based in {location}" if location else ""
    seniority_part = (
        f" It appears to be a {seniority.lower()} role."
        if seniority not in {"Unknown", "Not specified"}
        else ""
    )

    if required_skills:
        top_skills = ", ".join(required_skills[:4])
        skills_part = f" The role emphasizes skills such as {top_skills}."
    else:
        skills_part = ""

    return (
        f"{role}{company_part}{location_part} focuses on building and supporting software systems."
        f"{seniority_part}{skills_part}"
    ).strip()


def generate_placeholder_summary(job: Job) -> dict[str, Any]:
    """Generate a deterministic job summary from stored fields.

    This function generates a summary based on a few heuristics and stored job data. 
    It does not use any AI or external services, so it can be used as a fallback or baseline.

    Args:
        job: The job to summarize.

    Returns:
        A dictionary containing the summary, seniority, responsibilities, required skills,
        and nice-to-have skills.
    """
    description = job.description_clean or job.description_raw or ""
    skills = parse_skills_json(job.skills_json)
    seniority = _infer_seniority(job.title)
    responsibilities = _extract_responsibilities(description)
    required_skills, nice_to_have = _classify_skills(description, skills)
    summary = _build_summary(
        title=job.title,
        company=job.company,
        location=job.location,
        seniority=seniority,
        required_skills=required_skills,
    )

    if not responsibilities:
        responsibilities = [
            "Build and maintain application features.",
            "Collaborate with cross-functional partners.",
            "Support delivery of reliable software systems.",
        ]

    return {
        "summary": summary,
        "seniority": seniority,
        "responsibilities": responsibilities[:4],
        "required_skills": required_skills[:6],
        "nice_to_have": nice_to_have[:4],
    }