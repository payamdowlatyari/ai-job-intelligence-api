"""Service for fetching raw HTML from a URL using httpx."""

import httpx

DEFAULT_TIMEOUT = 15.0
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AIJobIntelligenceBot/1.0; +https://github.com/payamdowlatyari/ai-job-intelligence-api)"
    )
}


async def fetch_html(url: str) -> str:
    """Fetch the HTML content of the given URL.

    Args:
        url: The fully-qualified URL to retrieve.

    Returns:
        The response body as a decoded string.

    Raises:
        httpx.HTTPError: On any HTTP-level error (4xx / 5xx).
        httpx.TimeoutException: When the request exceeds DEFAULT_TIMEOUT seconds.
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=DEFAULT_HEADERS) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
