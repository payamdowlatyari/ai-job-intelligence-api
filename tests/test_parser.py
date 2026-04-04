"""Unit tests for the HTML parser service."""

from app.services.parser import parse_job_page

SAMPLE_HTML_BASIC = """
<html>
<head>
  <title>Senior Python Developer at Acme Corp</title>
  <meta property="og:title" content="Senior Python Developer">
</head>
<body>
  <h1>Senior Python Developer</h1>
  <p>Acme Corp is looking for an experienced Python developer.</p>
  <p>Location: San Francisco, CA</p>
</body>
</html>
"""

SAMPLE_HTML_JSON_LD = """
<html>
<head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    "title": "Backend Engineer",
    "hiringOrganization": {
      "@type": "Organization",
      "name": "TechStartup Inc"
    },
    "jobLocation": {
      "@type": "Place",
      "address": {
        "@type": "PostalAddress",
        "addressLocality": "Austin",
        "addressRegion": "TX",
        "addressCountry": "US"
      }
    },
    "description": "We are hiring a backend engineer with Python and FastAPI experience."
  }
  </script>
</head>
<body>
  <h1>Backend Engineer</h1>
</body>
</html>
"""

SAMPLE_HTML_MINIMAL = """
<html><body><p>A job description with no structured data.</p></body></html>
"""


def test_parse_title_from_h1() -> None:
    """Parser should extract title from the first h1 tag when no JSON-LD is present."""
    result = parse_job_page("https://example.com/job/1", SAMPLE_HTML_BASIC)
    assert result["title"] == "Senior Python Developer"


def test_parse_title_from_og_meta() -> None:
    """Parser should fall back to og:title meta when no h1 is present."""
    html = """
    <html><head>
      <meta property="og:title" content="Data Engineer">
    </head><body></body></html>
    """
    result = parse_job_page("https://example.com/job/2", html)
    assert result["title"] == "Data Engineer"


def test_parse_title_from_json_ld() -> None:
    """Parser should prefer the JSON-LD title over h1 and meta tags."""
    result = parse_job_page("https://example.com/job/3", SAMPLE_HTML_JSON_LD)
    assert result["title"] == "Backend Engineer"


def test_parse_company_from_json_ld() -> None:
    """Parser should extract company name from JSON-LD hiringOrganization."""
    result = parse_job_page("https://example.com/job/3", SAMPLE_HTML_JSON_LD)
    assert result["company"] == "TechStartup Inc"


def test_parse_location_from_json_ld() -> None:
    """Parser should construct a location string from JSON-LD address fields."""
    result = parse_job_page("https://example.com/job/3", SAMPLE_HTML_JSON_LD)
    assert result["location"] == "Austin, TX, US"


def test_parse_description_from_json_ld() -> None:
    """Parser should use the JSON-LD description when available."""
    result = parse_job_page("https://example.com/job/3", SAMPLE_HTML_JSON_LD)
    assert "FastAPI" in result["description_raw"]


def test_parse_description_fallback_to_body() -> None:
    """Parser should fall back to body text when no JSON-LD description exists."""
    result = parse_job_page("https://example.com/job/4", SAMPLE_HTML_MINIMAL)
    assert "job description" in result["description_raw"].lower()


def test_parse_source_is_netloc() -> None:
    """Parser should set source to the netloc of the provided URL."""
    result = parse_job_page("https://jobs.example.com/job/5", SAMPLE_HTML_MINIMAL)
    assert result["source"] == "jobs.example.com"


def test_parse_minimal_html_no_crash() -> None:
    """Parser should not raise an exception for minimal / sparse HTML."""
    result = parse_job_page("https://example.com/job/6", SAMPLE_HTML_MINIMAL)
    assert isinstance(result, dict)
    assert "title" in result
