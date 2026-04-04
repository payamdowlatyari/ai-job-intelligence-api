"""Service for parsing job data from raw HTML using BeautifulSoup."""

import json
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


def _get_json_ld_job(soup: BeautifulSoup) -> Optional[dict]:
    """Extract the first JSON-LD JobPosting block from the page, if present."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def _extract_title(soup: BeautifulSoup, json_ld: Optional[dict]) -> Optional[str]:
    """Return the best-effort job title from the page."""
    if json_ld and json_ld.get("title"):
        return json_ld["title"].strip()

    # Check common meta tags
    for meta_name in ("title", "og:title", "twitter:title"):
        tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
            "meta", attrs={"name": meta_name}
        )
        if tag and tag.get("content"):
            return tag["content"].strip()

    # First h1 on the page
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    # Fall back to <title>
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)

    return None


def _extract_company(soup: BeautifulSoup, json_ld: Optional[dict]) -> Optional[str]:
    """Return the best-effort company name from the page."""
    if json_ld:
        hiring_org = json_ld.get("hiringOrganization", {})
        if isinstance(hiring_org, dict) and hiring_org.get("name"):
            return hiring_org["name"].strip()

    for meta_name in ("og:site_name", "twitter:site"):
        tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
            "meta", attrs={"name": meta_name}
        )
        if tag and tag.get("content"):
            return tag["content"].strip()

    return None


def _extract_location(soup: BeautifulSoup, json_ld: Optional[dict]) -> Optional[str]:
    """Return the best-effort job location from the page."""
    if json_ld:
        job_location = json_ld.get("jobLocation", {})
        if isinstance(job_location, dict):
            address = job_location.get("address", {})
            if isinstance(address, dict):
                parts = filter(
                    None,
                    [
                        address.get("addressLocality"),
                        address.get("addressRegion"),
                        address.get("addressCountry"),
                    ],
                )
                combined = ", ".join(parts)
                if combined:
                    return combined

    return None


def _extract_description(soup: BeautifulSoup, json_ld: Optional[dict]) -> str:
    """Return the best-effort raw description text from the page."""
    if json_ld and json_ld.get("description"):
        return json_ld["description"].strip()

    # Remove non-content tags
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    body = soup.find("body")
    if body:
        return body.get_text(separator=" ", strip=True)

    return soup.get_text(separator=" ", strip=True)


def parse_job_page(url: str, html: str) -> dict:
    """Parse a job posting HTML page and return a structured dictionary.

    Args:
        url:  The source URL of the page.
        html: Raw HTML content of the page.

    Returns:
        A dictionary with keys: source, title, company, location, description_raw.
    """
    soup = BeautifulSoup(html, "html.parser")
    json_ld = _get_json_ld_job(soup)

    source = urlparse(url).netloc or url

    return {
        "source": source,
        "title": _extract_title(soup, json_ld),
        "company": _extract_company(soup, json_ld),
        "location": _extract_location(soup, json_ld),
        "description_raw": _extract_description(soup, json_ld),
    }
