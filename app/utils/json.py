"""Shared JSON parsing utilities."""

from __future__ import annotations

import json


def parse_skills_json(skills_json: str | None) -> list[str]:
    """Safely parse a JSON-encoded list of skills from the database.

    Args:
        skills_json: A JSON string representing a list of skill strings,
            or ``None`` / an empty string when no skills are stored.

    Returns:
        A list of non-empty skill strings, or an empty list if the input
        is absent or cannot be decoded.
    """
    if not skills_json:
        return []

    try:
        parsed = json.loads(skills_json)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    return []
