import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-5.4-mini"

def _get_client() -> OpenAI:
    """Return a lazily-created OpenAI client, raising clearly if the key is absent."""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Set it before calling cover letter functions."
            )
        client = OpenAI(api_key=api_key)
    return client


def build_cover_letter_prompt(
    *,
    resume_text: str,
    job_text: str,
    candidate_name: str = "",
    company: str = "",
    role_title: str = "",
    tone: str = "professional",
    length: str = "medium",
) -> str:
    return f"""
Write a tailored cover letter for the following job application.

Requirements:
- Tone: {tone}
- Length: {length}
- Be specific and grounded in the resume and job description
- Do not invent experience that is not present
- Avoid generic filler
- Make it sound natural and concise
- Return only the cover letter text, no markdown, no heading

Candidate name: {candidate_name or ""}
Company: {company or ""}
Role title: {role_title or ""}

Resume:
{resume_text}

Job description:
{job_text}
""".strip()


def generate_cover_letter(
    *,
    resume_text: str,
    job_text: str,
    candidate_name: str = "",
    company: str = "",
    role_title: str = "",
    tone: str = "professional",
    length: str = "medium",
) -> str:
    prompt = build_cover_letter_prompt(
        resume_text=resume_text,
        job_text=job_text,
        candidate_name=candidate_name,
        company=company,
        role_title=role_title,
        tone=tone,
        length=length,
    )

    client = _get_client()
    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": "You write strong, truthful, tailored software engineering cover letters."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    return response.output_text.strip()