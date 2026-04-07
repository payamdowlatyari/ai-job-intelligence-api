"""Service for parsing job data from raw HTML using BeautifulSoup."""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from app.utils.time import parse_relative_time

def _is_valid_location(value: str | None) -> bool:
    """Return True if the location string is valid."""

    if not value:
        return False

    # Reject long noisy text
    if len(value) > 60:
        return False

    # Reject sentences
    if "." in value:
        return False

    return True


def _clean_text(value: str | None) -> Optional[str]:
    """Normalize whitespace and return None for empty strings."""
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _looks_like_location(line: str) -> bool:
    """Return True if the line looks like a location."""
    return bool(
        re.search(
            r"\b(remote|united states|hybrid|on[- ]site|[A-Za-z\s]+,\s*[A-Z]{2})\b",
            line,
            re.IGNORECASE,
        )
    )


def _looks_like_relative_date(line: str) -> bool:
    """Return True if the line looks like a relative date."""
    return bool(
        re.search(
            r"\b\d+\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months)\s+ago\b",
            line,
            re.IGNORECASE,
        )
    )


def _extract_company_from_header(lines: list[str], title: Optional[str]) -> Optional[str]:
    """Extract company from lines immediately after title."""
    if not title:
        return None

    try:
        idx = next(i for i, line in enumerate(lines) if line == title)
    except StopIteration:
        return None

    nearby = lines[idx + 1 : idx + 8]

    for line in nearby:
        cleaned = _clean_text(line)
        if not cleaned:
            continue

        lowered = cleaned.lower()

        # Skip noise
        if _looks_like_location(cleaned):
            continue
        if _looks_like_relative_date(cleaned):
            continue
        if lowered in {
            "apply",
            "save",
            "report this job",
            "see who has hired for this role",
        }:
            continue

        # 🚨 NEW: skip LinkedIn junk phrases
        if "applicant" in lowered:
            continue
        if "hiring for this role" in lowered:
            continue

        # 🚨 NEW: reject long paragraphs
        if len(cleaned) > 60:
            continue

        # 🚨 NEW: reject sentences
        if "." in cleaned:
            continue

        return cleaned

    return None

def _get_json_ld_job(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    """Extract the first JSON-LD JobPosting block from the page, if present."""
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item

    return None


def _extract_title(soup: BeautifulSoup, json_ld: Optional[dict[str, Any]]) -> Optional[str]:
    """Return the best-effort job title from the page."""
    if json_ld and json_ld.get("title"):
        return _clean_text(str(json_ld["title"]))

    h1 = soup.find("h1")
    if h1:
        return _clean_text(h1.get_text(" ", strip=True))

    for meta_name in ("og:title", "twitter:title", "title"):
        tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
            "meta", attrs={"name": meta_name}
        )
        if tag and tag.get("content"):
            return _clean_text(tag["content"])

    title_tag = soup.find("title")
    if title_tag:
        return _clean_text(title_tag.get_text(" ", strip=True))

    return None


def _extract_company(soup: BeautifulSoup, json_ld: Optional[dict[str, Any]]) -> Optional[str]:
    """Return the best-effort company name from the page."""
    if json_ld:
        hiring_org = json_ld.get("hiringOrganization", {})
        if isinstance(hiring_org, dict) and hiring_org.get("name"):
            return _clean_text(str(hiring_org["name"]))

    for meta_name in ("og:site_name", "twitter:site"):
        tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
            "meta", attrs={"name": meta_name}
        )
        if tag and tag.get("content"):
            value = _clean_text(tag["content"])
            if value and value.lower() not in {"linkedin", "@linkedin"}:
                return value

    return None


def _extract_location_from_json_ld(json_ld: Optional[dict[str, Any]]) -> Optional[str]:
    """Extract location from JSON-LD JobPosting if available."""
    if not json_ld:
        return None

    job_location = json_ld.get("jobLocation")
    address = None

    if isinstance(job_location, list) and job_location:
        first = job_location[0]
        if isinstance(first, dict):
            address = first.get("address")
    elif isinstance(job_location, dict):
        address = job_location.get("address")

    if isinstance(address, dict):
        parts = [
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("addressCountry"),
        ]
        combined = ", ".join(str(part).strip() for part in parts if part)
        return _clean_text(combined)

    return None


def _extract_date_posted_from_json_ld(json_ld: Optional[dict[str, Any]]) -> Optional[str]:
    """Extract datePosted from JSON-LD if available."""
    if not json_ld:
        return None
    return _clean_text(json_ld.get("datePosted"))


def _extract_job_type_from_json_ld(json_ld: Optional[dict[str, Any]]) -> Optional[str]:
    """Extract employment type from JSON-LD if available."""
    if not json_ld:
        return None

    employment_type = json_ld.get("employmentType")
    if isinstance(employment_type, list):
        return _clean_text(", ".join(str(item) for item in employment_type if item))
    return _clean_text(str(employment_type)) if employment_type else None


def _get_visible_text_lines(soup: BeautifulSoup) -> list[str]:
    """Return cleaned visible text lines from the page."""
    lines: list[str] = []
    for text in soup.stripped_strings:
        cleaned = _clean_text(text)
        if cleaned:
            lines.append(cleaned)
    return lines


def _extract_linkedin_location(lines: list[str]) -> Optional[str]:
    """Extract location from LinkedIn-style header lines."""
    for line in lines:
        if re.search(r"\b(remote|united states|[A-Za-z\s]+,\s*[A-Z]{2})\b", line, re.IGNORECASE):
            return _clean_text(line)
    return None


def _extract_header_fields(
    soup: BeautifulSoup,
    fallback_title: Optional[str],
    fallback_company: Optional[str],
) -> dict[str, Optional[str]]:
    """Extract fields from visible header-like text near the title."""
    result = {
        "company": fallback_company,
        "location": None,
        "date_posted": None,
        "job_type": None,
    }

    lines = _get_visible_text_lines(soup)
    if not lines:
        return result

    title = fallback_title
    if not title:
        return result

    try:
        title_index = next(i for i, line in enumerate(lines) if line == title)
    except StopIteration:
        return result

    nearby = lines[title_index + 1 : title_index + 12]

    location_pattern = re.compile(
        r"""
        (
            \bremote\b |
            \bhybrid\b |
            \bon[-\s]?site\b |
            [A-Z][A-Za-z.\s'-]+,\s?[A-Z]{2}\b |
            [A-Z][A-Za-z.\s'-]+,\s?[A-Z][A-Za-z.\s'-]+
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    date_pattern = re.compile(
        r"\b(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months)\s+ago\b",
        re.IGNORECASE,
    )

    job_type_pattern = re.compile(
        r"\b(full[-\s]?time|part[-\s]?time|contract|temporary|internship|intern|apprenticeship)\b",
        re.IGNORECASE,
    )

    for line in nearby:
        lowered = line.lower()

        if not result["company"]:
            if (
                "applicant" not in lowered
                and "ago" not in lowered
                and not location_pattern.search(line)
                and len(line) < 120
            ):
                result["company"] = line
                continue

        # after computing nearby
        if not result["location"]:
            linkedin_loc = _extract_linkedin_location(nearby)
            if linkedin_loc:
                result["location"] = linkedin_loc

        date_match = date_pattern.search(line)
        if date_match:
            result["date_posted"] = _clean_text(date_match.group(0))

        if not result["job_type"] and job_type_pattern.search(line):
            match = job_type_pattern.search(line)
            if match:
                result["job_type"] = _clean_text(match.group(1))

    return result


def _extract_labeled_value(full_text: str, labels: list[str]) -> Optional[str]:
    """Extract value after label with better stopping logic."""
    for label in labels:
        pattern = rf"{re.escape(label)}\s*:?\s*(.+)"
        match = re.search(pattern, full_text, flags=re.IGNORECASE)
        if not match:
            continue

        value = match.group(1).strip()

        # STOP at common boundaries
        value = re.split(
            r"\s{2,}|[\n]|(?=\b[A-Z][a-zA-Z ]{2,}:)|(?=\b[A-Z][a-z]+\s[A-Z][a-z]+)",
            value
        )[0]

        # Limit runaway text
        if len(value) > 80:
            value = value[:80]

        return _clean_text(value.strip(" •-"))

    return None


def _extract_company_from_linkedin_text(full_text: str) -> Optional[str]:
    """Try a LinkedIn-specific text fallback for company name."""
    patterns = [
        r"Company\s*:?\s*(.+)",
        r"About the job\s+(.+?)\s+is hiring",
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text, flags=re.IGNORECASE)
        if match:
            value = _clean_text(match.group(1))
            if value:
                return value

    return None


def _extract_description(soup: BeautifulSoup, json_ld: Optional[dict[str, Any]]) -> str:
    """Return the best-effort raw description text from the page."""
    if json_ld and json_ld.get("description"):
        description = _clean_text(str(json_ld["description"]))
        if description:
            return description

    soup_copy = BeautifulSoup(str(soup), "html.parser")
    for tag in soup_copy(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    body = soup_copy.find("body")
    if body:
        return body.get_text(separator=" ", strip=True)

    return soup_copy.get_text(separator=" ", strip=True)


def parse_job_page(url: str, html: str) -> dict[str, Optional[str]]:
    """Parse a job posting HTML page and return structured fields.

    Returns:
        A dictionary with keys:
        - source
        - title
        - company
        - location
        - date_posted
        - job_type
        - description_raw
    """
    soup = BeautifulSoup(html, "html.parser")
    json_ld = _get_json_ld_job(soup)
    full_text = soup.get_text("\n", strip=True)

    source = urlparse(url).netloc.replace("www.", "") or url
    title = _extract_title(soup, json_ld)

    # STEP 1: extract header fields
    company_raw = _extract_company(soup, json_ld)
    header_fields = _extract_header_fields(soup, title, company_raw)
    lines = _get_visible_text_lines(soup)

    # STEP 2: detect bad company
    def _is_bad_company(value: str | None) -> bool:
        if not value:
            return True
        return value.lower() in {"linkedin", "@linkedin"}

    # STEP 3: header extraction (force override if bad)
    header_company = _extract_company_from_header(lines, title)

    company = (
        company_raw if not _is_bad_company(company_raw) else None
        or header_company
        or _extract_company_from_linkedin_text(full_text)
    )

    location = (
        _extract_location_from_json_ld(json_ld)
        or header_fields.get("location")
        or _extract_labeled_value(full_text, ["Location"])
    )

    if not _is_valid_location(location):
        location = None

    date_posted_raw = (
        _extract_date_posted_from_json_ld(json_ld)
        or header_fields.get("date_posted")
        or _extract_labeled_value(full_text, ["Date Posted", "Posted", "Posted On"])
    )
    
    date_posted_dt = parse_relative_time(date_posted_raw)
    date_posted = date_posted_dt.isoformat() if date_posted_dt else None

    job_type = (
        _extract_job_type_from_json_ld(json_ld)
        or header_fields.get("job_type")
        or _extract_labeled_value(
            full_text,
            ["Employment type", "Job type", "Full/Part-Time", "Schedule"],
        )
    )

    return {
        "source": source,
        "title": title,
        "company": company,
        "location": location,
        "date_posted": date_posted,
        "job_type": job_type,
        "description_raw": _extract_description(soup, json_ld),
    }
