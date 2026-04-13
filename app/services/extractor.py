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

# ---------------------------------------------------------------------------
# Boilerplate patterns to strip from scraped job descriptions.
# Each pattern is compiled with IGNORECASE and DOTALL where needed.
# ---------------------------------------------------------------------------

# Phrases that appear verbatim (or nearly so) on LinkedIn and similar sites.
_BOILERPLATE_PHRASES: list[str] = [
    r"Agree\s*&\s*Join\s+LinkedIn",
    r"By clicking Continue to join or sign in,\s*you agree to LinkedIn'?s?\s*User Agreement\s*,?\s*Privacy Policy\s*,?\s*and\s*Cookie Policy\s*\.?",
    r"Skip to main content",
    r"Join or sign in to find your next job",
    r"Join to apply for the .+? role at .+?",
    r"Email or phone\s*Password\s*Show\s*Forgot password\?\s*Sign in",
    r"Sign in with Email or",
    r"New to LinkedIn\?\s*Join now",
    r"Sign in to create job alert",
    r"Save\s+Report this job",
    r"Referrals increase your chances of interviewing at .+? by \d+x",
    r"See who you know",
    r"Get notified about new .+? jobs in .+?\.",
    r"See who .+? has hired for this role",
    r"Show more\s*Show less",
    r"Show more jobs like this\s*Show fewer jobs like this",
    r"You'?re signed out\s*Sign in for the full experience\.?",
    r"Sign in\s*Join now",
    r"Save time applying to future jobs.+?Join now",
    r"Explore top content on LinkedIn.+?View top content",
    r"Find curated posts and insights.+?all in one place\.?",
    r"provided pay range\s*This range is provided by .+?talk with your recruiter to learn more\.",
]

_BOILERPLATE_RE = re.compile(
    "|".join(_BOILERPLATE_PHRASES),
    re.IGNORECASE | re.DOTALL,
)

# Sections that appear after the actual job content on LinkedIn.
_TAIL_MARKERS: list[str] = [
    r"Seniority level\s",
    r"Similar jobs\b",
    r"People also viewed\b",
    r"Similar Searches\b",
    r"More searches\b",
    r"Featured Benefits\b",
]

_TAIL_RE = re.compile(
    "|".join(_TAIL_MARKERS),
    re.IGNORECASE,
)

# Repeated navigation / UI fragments (e.g. "Sign in Sign in").
_UI_FRAGMENTS_RE = re.compile(
    r"\b(?:Sign in|Join now|Apply)\b(?:\s+(?:Sign in|Join now|Apply)\b)+",
    re.IGNORECASE,
)

# Counts like "139 applicants" or "2 days ago" that leak from UI chrome.
_APPLICANT_COUNT_RE = re.compile(r"\b\d+\s+applicants?\b", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Normalize whitespace, strip non-printable characters, and remove
    common scraping boilerplate (LinkedIn sign-in prompts, footer sections,
    similar-jobs listings, etc.).

    Args:
        text: Raw input text.

    Returns:
        Cleaned, whitespace-normalised string.
    """
    # Collapse whitespace early so later patterns can assume single spaces.
    text = re.sub(r"\s+", " ", text)

    # Remove non-printable characters.
    text = re.sub(r"[^\x20-\x7E]", "", text)

    # Cut everything from the first "tail" marker onward (similar jobs, etc.).
    tail_match = _TAIL_RE.search(text)
    if tail_match:
        text = text[: tail_match.start()]

    # Strip known boilerplate phrases.
    text = _BOILERPLATE_RE.sub(" ", text)

    # Remove repeated UI fragments.
    text = _UI_FRAGMENTS_RE.sub(" ", text)

    # Remove applicant count noise.
    text = _APPLICANT_COUNT_RE.sub(" ", text)

    # Final whitespace cleanup.
    text = re.sub(r"\s+", " ", text)
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
