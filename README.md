# AI Job Intelligence API

A lightweight Python backend that fetches public job posting pages from the web, extracts structured data, stores it in SQLite, and exposes REST API endpoints for ingestion, listing, AI summarisation, and skill-match scoring.

---

## Project Overview

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| ORM / DB | SQLModel + SQLite |
| HTTP client | httpx (async) |
| HTML parsing | BeautifulSoup4 |
| Schema validation | Pydantic v2 |
| Config | python-dotenv |
| Tests | pytest |

---

## Setup Instructions

### 1. Prerequisites

- Python 3.12+

### 2. Clone and install dependencies

```bash
git clone https://github.com/payamdowlatyari/ai-job-intelligence-api.git
cd ai-job-intelligence-api
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env if needed (defaults are fine for local development)
```

---

## Running Locally

```bash
uvicorn app.main:app --reload
```

The API will be available at <http://localhost:8000>.

Interactive API docs (Swagger UI): <http://localhost:8000/docs>

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Example API Endpoints

### Health check

```
GET /health
```

```json
{"status": "ok"}
```

### Ingest job postings

```
POST /jobs/ingest
Content-Type: application/json

{
  "urls": [
    "https://example.com/jobs/senior-python-dev",
    "https://example.com/jobs/backend-engineer"
  ]
}
```

### List jobs (with optional filters)

```
GET /jobs?keyword=python&company=acme&location=remote
```

### Get a single job

```
GET /jobs/{job_id}
```

### Summarise a job

```
POST /jobs/{job_id}/summarize
```

### Match skills against a job

```
POST /jobs/{job_id}/match
Content-Type: application/json

{
  "skills": ["Python", "FastAPI", "Docker"],
  "resume_text": "Optional free-form resume text — skills are extracted automatically."
}
```

---

## Project Structure

```
ai-job-intelligence-api/
  app/
    main.py          # FastAPI app, router registration, startup hooks
    config.py        # Environment variable loading
    db.py            # SQLite engine, session dependency
    models.py        # Job SQLModel table
    schemas.py       # Pydantic request/response schemas
    routes/
      jobs.py        # POST /jobs/ingest, GET /jobs, GET /jobs/{id}
      summarize.py   # POST /jobs/{id}/summarize
      match.py       # POST /jobs/{id}/match
    services/
      fetcher.py     # async fetch_html(url)
      parser.py      # parse_job_page(url, html) → dict
      extractor.py   # clean_text, extract_skills
      summarizer.py  # generate_placeholder_summary(job)
      matcher.py     # match_job(job_skills, candidate_skills)
    utils/
      text.py        # truncate, slugify helpers
  tests/
    test_jobs.py     # API integration tests
    test_parser.py   # HTML parser unit tests
    test_matcher.py  # Matcher unit tests
  requirements.txt
  .env.example
  README.md
```

---

## Current Limitations

- **No real LLM integration** — the `/summarize` endpoint uses simple heuristics.- **Rule-based skill extraction** — only a fixed keyword list is supported.
- **SQLite** — not suitable for production concurrent workloads.
- **No authentication** — all endpoints are public.
- **Basic HTML parsing** — works best with structured pages that include JSON-LD.

---

## Future Improvements

- Integrate OpenAI / Anthropic / local LLM for real summarisation.
- Expand skill extraction with NLP (spaCy, sentence-transformers).
- Swap SQLite for PostgreSQL in production.
- Add JWT authentication and rate limiting.
- Build a background task queue (Celery / ARQ) for async ingestion.
- Add pagination to `GET /jobs`.
- Cache fetched HTML to avoid redundant network requests.
