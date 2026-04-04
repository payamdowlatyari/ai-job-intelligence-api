"""Unit tests for the matcher service."""

from app.services.matcher import match_job


def test_perfect_match() -> None:
    """When candidate has all job skills the fit score should be 100."""
    job_skills = ["Python", "FastAPI", "Docker"]
    candidate_skills = ["Python", "FastAPI", "Docker"]
    result = match_job(job_skills, candidate_skills)
    assert result["fit_score"] == 100.0
    assert set(result["matched_skills"]) == set(job_skills)
    assert result["missing_skills"] == []


def test_no_match() -> None:
    """When candidate shares no skills with the job the fit score should be 0."""
    job_skills = ["Kubernetes", "Go"]
    candidate_skills = ["Python", "React"]
    result = match_job(job_skills, candidate_skills)
    assert result["fit_score"] == 0.0
    assert result["matched_skills"] == []
    assert set(result["missing_skills"]) == set(job_skills)


def test_partial_match() -> None:
    """Fit score should reflect the fraction of job skills that the candidate has."""
    job_skills = ["Python", "Docker", "AWS", "Kubernetes"]
    candidate_skills = ["Python", "Docker"]
    result = match_job(job_skills, candidate_skills)
    assert result["fit_score"] == 50.0
    assert set(result["matched_skills"]) == {"Python", "Docker"}
    assert set(result["missing_skills"]) == {"AWS", "Kubernetes"}


def test_empty_job_skills() -> None:
    """When the job has no skills, fit score should be 0 with an informative note."""
    result = match_job([], ["Python"])
    assert result["fit_score"] == 0.0
    assert "No skills found" in result["notes"]


def test_empty_candidate_skills() -> None:
    """When the candidate provides no skills, fit score should be 0."""
    result = match_job(["Python", "AWS"], [])
    assert result["fit_score"] == 0.0
    assert result["matched_skills"] == []


def test_case_insensitive_matching() -> None:
    """Skill matching should be case-insensitive."""
    job_skills = ["Python", "Docker"]
    candidate_skills = ["python", "DOCKER"]
    result = match_job(job_skills, candidate_skills)
    assert result["fit_score"] == 100.0


def test_strong_match_note() -> None:
    """Fit score >= 80 should produce a 'Strong match' note."""
    job_skills = ["Python", "FastAPI", "Docker", "AWS", "SQL"]
    candidate_skills = ["Python", "FastAPI", "Docker", "AWS", "SQL"]
    result = match_job(job_skills, candidate_skills)
    assert "Strong" in result["notes"]


def test_weak_match_note() -> None:
    """Fit score < 50 should produce a 'Weak match' note."""
    job_skills = ["Python", "FastAPI", "Docker", "AWS", "SQL", "Kubernetes", "Redis"]
    candidate_skills = ["Python"]
    result = match_job(job_skills, candidate_skills)
    assert "Weak" in result["notes"]
