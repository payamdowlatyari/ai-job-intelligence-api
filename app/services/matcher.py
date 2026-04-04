"""Service for computing a skill-overlap match score between a job and a candidate."""

from typing import Any, Dict, List


def match_job(job_skills: List[str], candidate_skills: List[str]) -> Dict[str, Any]:
    """Compute a simple overlap-based fit score between job and candidate skills.

    Args:
        job_skills:       Skills extracted from the job posting.
        candidate_skills: Skills provided by or extracted from the candidate.

    Returns:
        A dictionary with keys:
            fit_score     – float 0–100 representing percentage overlap.
            matched_skills – skills present in both lists.
            missing_skills – job skills absent from the candidate profile.
            notes          – human-readable summary of the match quality.
    """
    # Normalize to lower-case sets for comparison
    job_set = {s.lower() for s in job_skills}
    candidate_set = {s.lower() for s in candidate_skills}

    if not job_set:
        return {
            "fit_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "notes": "No skills found in the job posting to compare against.",
        }

    # Preserve original casing from job_skills for output
    job_skill_map = {s.lower(): s for s in job_skills}

    matched_lower = job_set & candidate_set
    missing_lower = job_set - candidate_set

    matched_skills = [job_skill_map[s] for s in sorted(matched_lower)]
    missing_skills = [job_skill_map[s] for s in sorted(missing_lower)]

    fit_score = round(len(matched_lower) / len(job_set) * 100, 2)

    if fit_score >= 80:
        notes = "Strong match — most required skills are present."
    elif fit_score >= 50:
        notes = "Moderate match — some key skills are missing."
    else:
        notes = "Weak match — significant skill gaps detected."

    return {
        "fit_score": fit_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "notes": notes,
    }
