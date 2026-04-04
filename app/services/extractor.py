"""Service for cleaning text and extracting skills from job descriptions."""

import re
from typing import List

# Predefined skill keyword list (case-insensitive matching, preserved casing in output)
SKILL_KEYWORDS: List[str] = [
    "Python",
    "JavaScript",
    "TypeScript",
    "React",
    "Next.js",
    "Node.js",
    "FastAPI",
    "Django",
    "Flask",
    "AWS",
    "Docker",
    "Kubernetes",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "Redis",
    "OpenSearch",
    "Elasticsearch",
    "Git",
    "CI/CD",
]

# Pre-compile patterns for performance
_SKILL_PATTERNS = [(skill, re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE)) for skill in SKILL_KEYWORDS]


def clean_text(text: str) -> str:
    """Normalize whitespace and strip non-printable characters from text.

    Args:
        text: Raw input text.

    Returns:
        Cleaned, whitespace-normalised string.
    """
    # Collapse whitespace sequences (spaces, tabs, newlines) into a single space
    text = re.sub(r"\s+", " ", text)
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E]", "", text)
    return text.strip()


def extract_skills(text: str) -> List[str]:
    """Extract known skill keywords from text using rule-based matching.

    Args:
        text: Cleaned or raw text to scan for skill mentions.

    Returns:
        Deduplicated list of matched skills in their canonical casing.    """
    found: List[str] = []
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            found.append(skill)
    return found
