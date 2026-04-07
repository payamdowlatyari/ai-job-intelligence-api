"""Integration / API tests for the jobs and health endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.db import get_session

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="session")
def session_fixture():
    """Provide an in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Provide a TestClient with the in-memory database injected."""

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client: TestClient) -> None:
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "AI Job Intelligence API is healthy and running! ✅"}



# ---------------------------------------------------------------------------
# GET /jobs (empty state)
# ---------------------------------------------------------------------------

def test_list_jobs_empty(client: TestClient) -> None:
    """GET /jobs on an empty database should return an empty list."""
    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["jobs"] == []


# ---------------------------------------------------------------------------
# GET /jobs/{job_id} — not found
# ---------------------------------------------------------------------------

def test_get_job_not_found(client: TestClient) -> None:
    """GET /jobs/999 for a non-existent job should return 404."""
    response = client.get("/jobs/999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /jobs/ingest — mocked fetcher
# ---------------------------------------------------------------------------

MOCK_HTML = """
<html>
<head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org/",
    "@type": "JobPosting",
    "title": "Python Developer",
    "hiringOrganization": {"@type": "Organization", "name": "MockCorp"},
    "description": "We need Python, FastAPI, Docker skills."
  }
  </script>
</head>
<body><h1>Python Developer</h1></body>
</html>
"""


@patch("app.services.fetcher.fetch_html", new_callable=AsyncMock, return_value=MOCK_HTML)
def test_ingest_job(mock_fetch, client: TestClient) -> None:
    """POST /jobs/ingest should fetch, parse and store a job then return it."""
    payload = {"urls": ["https://example.com/job/python-dev"]}
    response = client.post("/jobs/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ingested_count"] == 1
    job = data["jobs"][0]
    assert job["title"] == "Python Developer"
    assert job["company"] == "MockCorp"
    assert "Python" in job["skills_json"]


@patch("app.services.fetcher.fetch_html", new_callable=AsyncMock, return_value=MOCK_HTML)
def test_ingest_duplicate_url(mock_fetch, client: TestClient) -> None:
    """Ingesting the same URL twice should not create a duplicate record."""
    payload = {"urls": ["https://example.com/job/dup"]}
    client.post("/jobs/ingest", json=payload)
    response = client.post("/jobs/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["existing_count"] == 1
    # Fetcher should only have been called once
    assert mock_fetch.call_count == 1


@patch("app.services.fetcher.fetch_html", new_callable=AsyncMock, return_value=MOCK_HTML)
def test_get_job_after_ingest(mock_fetch, client: TestClient) -> None:
    """After ingestion, GET /jobs/{job_id} should return the stored job."""
    payload = {"urls": ["https://example.com/job/get-test"]}
    ingest_response = client.post("/jobs/ingest", json=payload)
    job_id = ingest_response.json()["jobs"][0]["id"]

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id


@patch("app.services.fetcher.fetch_html", new_callable=AsyncMock, return_value=MOCK_HTML)
def test_list_jobs_after_ingest(mock_fetch, client: TestClient) -> None:
    """After ingestion, GET /jobs should list the stored job."""
    payload = {"urls": ["https://example.com/job/list-test"]}
    client.post("/jobs/ingest", json=payload)

    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@patch("app.services.fetcher.fetch_html", new_callable=AsyncMock, return_value=MOCK_HTML)
def test_summarize_job(mock_fetch, client: TestClient) -> None:
    """POST /jobs/{job_id}/summarize should return a SummarizeResponse."""
    payload = {"urls": ["https://example.com/job/summarize-test"]}
    ingest_response = client.post("/jobs/ingest", json=payload)
    job_id = ingest_response.json()["jobs"][0]["id"]

    response = client.post(f"/jobs/{job_id}/summarize")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "summary" in data
    assert isinstance(data["responsibilities"], list)
    assert isinstance(data["required_skills"], list)
    assert isinstance(data["nice_to_have"], list)


@patch("app.services.fetcher.fetch_html", new_callable=AsyncMock, return_value=MOCK_HTML)
def test_match_job(mock_fetch, client: TestClient) -> None:
    """POST /jobs/{job_id}/match should return a MatchResponse."""
    payload = {"urls": ["https://example.com/job/match-test"]}
    ingest_response = client.post("/jobs/ingest", json=payload)
    job_id = ingest_response.json()["jobs"][0]["id"]

    match_payload = {"skills": ["Python", "Docker"]}
    response = client.post(f"/jobs/{job_id}/match", json=match_payload)
    assert response.status_code == 200
    data = response.json()
    assert "fit_score" in data
    assert isinstance(data["matched_skills"], list)
    assert isinstance(data["missing_skills"], list)
    assert "notes" in data
