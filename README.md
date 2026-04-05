# AI Job Intelligence API

A lightweight Python backend that **ingests public job postings from the web**, transforms unstructured HTML into structured data, and provides **AI-powered insights** such as job summaries and candidate fit scoring.

---

## 🚀 Overview

Job postings are scattered across the web in inconsistent formats. This project solves that by:

1. **Fetching** job pages from public URLs
2. **Parsing & normalizing** messy HTML into a consistent schema
3. **Extracting skills** using rule-based NLP
4. **Providing APIs** to:
   - search jobs
   - summarize roles
   - match candidates to jobs

This demonstrates a real-world backend system combining **data ingestion + API design + applied AI**.

---

## 🧩 Features

### 🔍 Job Ingestion

- Fetch job postings from public URLs
- Parse structured data (title, company, location, description)
- Extract and normalize skills
- Handle duplicates and failures gracefully

### 📄 Job Retrieval

- List jobs with filters:
  - keyword
  - company
  - location

- Retrieve detailed job records

### 🧠 AI-Powered Summarization

- Generate structured summaries:
  - role overview
  - responsibilities
  - required skills
  - nice-to-have skills
  - inferred seniority

### 🎯 Candidate Match Scoring

- Match a candidate using:
  - skill list OR resume text

- Returns:
  - fit score (0–100)
  - matched skills
  - missing skills
  - extra skills
  - explanation notes

---

## 🏗️ Architecture

```
FastAPI
 ├── Routes (API layer)
 ├── Services (business logic)
 │     ├── Fetcher (web requests)
 │     ├── Parser (HTML → structured data)
 │     ├── Extractor (skills + cleaning)
 │     ├── Matcher (scoring logic)
 │     └── Summarizer (heuristic AI)
 ├── Models (SQLModel / SQLite)
 └── Schemas (Pydantic)
```

### Key Design Decisions

- **FastAPI** → lightweight, async, built-in Swagger
- **SQLite** → simple persistence for MVP
- **Rule-based NLP first** → deterministic, explainable, cheap
- **Service layer separation** → clean, testable architecture
- **Batch ingestion** → partial success handling (important for real systems)

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd ai-job-intelligence-api
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

### 5. Open API docs

```
http://127.0.0.1:8000/docs
```

---

## 📡 API Endpoints

### Health

```
GET /health
```

---

### Ingest Jobs

```
POST /jobs/ingest
```

**Request**

```json
{
  "urls": ["https://company.com/careers/software-engineer"]
}
```

**Response**

```json
{
  "ingested_count": 1,
  "existing_count": 0,
  "failed_count": 0,
  "jobs": [...],
  "failures": []
}
```

---

### List Jobs

```
GET /jobs?keyword=python&location=remote
```

---

### Get Job

```
GET /jobs/{job_id}
```

---

### Summarize Job

```
POST /jobs/{job_id}/summarize
```

**Response**

```json
{
  "job_id": 1,
  "summary": "Backend-focused role building scalable services...",
  "seniority": "Senior",
  "responsibilities": [...],
  "required_skills": [...],
  "nice_to_have": [...]
}
```

---

### Match Candidate to Job

```
POST /jobs/{job_id}/match
```

**Request**

```json
{
  "skills": ["Python", "FastAPI", "AWS", "SQL"]
}
```

OR

```json
{
  "resume_text": "5 years building backend APIs using Python and AWS..."
}
```

**Response**

```json
{
  "job_id": 1,
  "fit_score": 78,
  "candidate_skills": [...],
  "matched_skills": [...],
  "missing_skills": [...],
  "extra_candidate_skills": [...],
  "notes": "Moderate match — several relevant skills are present."
}
```

---

## 🧠 How “AI” is Used

This project intentionally starts with **lightweight, explainable AI techniques**:

- Skill extraction via keyword-based NLP
- Heuristic summarization
- Deterministic match scoring

### Why?

- Faster to build
- Easier to debug
- More predictable than LLM-only approaches

### Future improvements:

- LLM-based summarization
- embedding-based semantic search
- resume-job semantic matching

---

## 🧪 Testing

```bash
pytest
```

Includes:

- parser tests
- matcher tests
- API tests (with mocked services)

---

## ⚖️ Tradeoffs

| Decision              | Tradeoff                                   |
| --------------------- | ------------------------------------------ |
| SQLite                | Simple, but not scalable                   |
| Rule-based extraction | Fast & explainable, but less flexible      |
| In-memory filtering   | Easy, but not efficient for large datasets |
| No async DB           | Simpler, but less scalable                 |

---

## 🔮 Future Improvements

- Add vector search (FAISS / OpenSearch)
- Add real LLM integration
- Support multiple job sources automatically
- Scheduled ingestion pipeline
- Frontend dashboard (Next.js)
- Resume upload + parsing

---

## 💡 Why This Project Stands Out

This is not just a CRUD API. It demonstrates:

- Real-world **web data ingestion**
- Handling **messy unstructured data**
- Clean **backend architecture**
- Applied **AI/ML thinking**
- Clear **product use case**

---

## 📌 Example Demo Flow

1. Ingest a public job URL
2. View structured job data
3. Generate AI summary
4. Match candidate skills

---

## 👤 Author

Built as a portfolio project to demonstrate full-stack backend + AI capabilities.
