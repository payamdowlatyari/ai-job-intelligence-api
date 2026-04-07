import os
from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a lazily-created OpenAI client, raising clearly if the key is absent."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Set it before calling explain_match."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def explain_match(resume_text: str, job_text: str) -> str:
    """
    Generate a brief explanation of why a candidate is a good match for a job based on their resume and the job description.

    Args:
        resume_text (str): The text of the candidate's resume.
        job_text (str): The text of the job description.

    Returns:
        str: A brief explanation (2 sentences) of why the candidate is a good match for the job.
    """
    client = _get_client()
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {
                "role": "system",
                "content": "Explain briefly why the candidate is a good match for the job in 2 sentences."
            },
            {
                "role": "user",
                "content": f"Resume:\n{resume_text}\n\nJob:\n{job_text}"
            },
        ],
    )
    return response.output_text.strip()