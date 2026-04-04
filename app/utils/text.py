"""Shared text utility helpers."""

import re


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate text to at most *max_chars* characters, appending ellipsis if needed.

    Args:
        text:      Input string.
        max_chars: Maximum allowed character length.

    Returns:
        The original string if short enough, otherwise a truncated version ending in '…'.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def slugify(text: str) -> str:
    """Convert text to a URL-friendly lowercase slug.

    Args:
        text: Input string.

    Returns:
        Lowercased string with non-alphanumeric characters replaced by hyphens.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
