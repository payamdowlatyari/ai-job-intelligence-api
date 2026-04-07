import json
import math
import os
import time
from typing import Iterable, List

from openai import OpenAI, RateLimitError

from app.services.cache_utils import text_cache_key
from app.services.local_cache import TTLCache

_client: OpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # expected output dimension for this model
MAX_BATCH_SIZE = 20
MAX_RETRIES = 3

# Good for repeated resume/profile embeddings during one server lifecycle
resume_embedding_cache = TTLCache(ttl_seconds=3600, max_items=200)


def _get_client() -> OpenAI:
    """Return a lazily-created OpenAI client, raising clearly if the key is absent."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Set it before calling embedding functions."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def build_job_text(job) -> str:
    """
    Builds a single text block from a job object for embedding-based matching.
    It combines relevant fields into a single string, with each field separated by a newline.
    The resulting string is suitable for passing to OpenAI's text-embedding-3-small model.
    """

    parts = [
        f"Title: {job.title or ''}",
        f"Company: {job.company or ''}",
        f"Location: {job.location or ''}",
        f"Employment type: {job.employment_type or ''}",
        f"Job type: {job.job_type or ''}",
        f"Skills: {job.skills_json or ''}",
        f"Summary: {job.summary or ''}",
        f"Description: {job.description_clean or job.description_raw or ''}",
    ]
    return "\n".join(part for part in parts if part.strip()).strip()


def dumps_embedding(vector: List[float]) -> str:
    """
    Serialize a list of floats into a JSON string.
    This is used to store the embedding vector in the database as a string.
    """

    return json.dumps(vector)


def loads_embedding(value: str) -> List[float]:
    """
    Deserialize a JSON string into a list of floats.
    Malformed or unexpected data is treated as a missing embedding.
    """

    if not value:
        return []

    try:
        vector = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(vector, list):
        return []

    return vector


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Compute the cosine similarity between two vectors.

    The cosine similarity is a measure of how similar two non-zero vectors are in a multi-dimensional space.
    It is defined as the dot product of the two vectors divided by the product of their magnitudes.

    It ranges from -1 (completely different) to 1 (completely similar).
    If either of the vectors is zero, the cosine similarity is 0.
    """

    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def _sleep_backoff(attempt: int) -> None:
    # 1s, 2s, 4s
    """
    Sleep for an exponentially increasing amount of time based on the attempt number.
    This is used to back off when encountering transient rate limit errors.
    """
    
    time.sleep(2 ** attempt)


def _create_embeddings(inputs: list[str]) -> list[list[float]]:
    """
    Batched embeddings request. OpenAI's embeddings API accepts multiple inputs
    in one call, which reduces request count substantially.
    """

    client = _get_client()
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=inputs,
            )
            vectors = [item.embedding for item in response.data]
            for vector in vectors:
                if len(vector) != EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Unexpected embedding dimension {len(vector)}; "
                        f"expected {EMBEDDING_DIMENSION} for model {EMBEDDING_MODEL}."
                    )
            return vectors
        except RateLimitError as exc:
            # Retry transient rate-limit conditions only.
            # insufficient_quota should not be retried aggressively.
            error_str = str(exc).lower()
            if "insufficient_quota" in error_str:
                raise
            if attempt == MAX_RETRIES - 1:
                raise
            _sleep_backoff(attempt)

    return []


def get_embedding(text: str, use_local_cache: bool = True) -> List[float]:
    """
    Get an embedding vector for a given text.

    The embedding vector is a dense numerical representation of the input text.
    It is computed using the OpenAI embeddings API.

    If use_local_cache is True, the result is cached for future requests.
    """

    text = (text or "").strip()
    if not text:
        return []

    cache_key = text_cache_key(text)

    if use_local_cache:
        cached = resume_embedding_cache.get(cache_key)
        if cached is not None:
            return cached

    vectors = _create_embeddings([text])
    vector = vectors[0] if vectors else []

    if use_local_cache and vector:
        resume_embedding_cache.set(cache_key, vector)

    return vector


def get_embeddings_batched(texts: Iterable[str]) -> list[list[float]]:
    """
    Get embedding vectors for a batch of texts.
    This function processes the input texts in batches to optimize API usage and reduce latency.
    """

    cleaned = [(text or "").strip() for text in texts]
    cleaned = [text for text in cleaned if text]

    if not cleaned:
        return []

    all_vectors: list[list[float]] = []

    for i in range(0, len(cleaned), MAX_BATCH_SIZE):
        chunk = cleaned[i : i + MAX_BATCH_SIZE]
        vectors = _create_embeddings(chunk)
        all_vectors.extend(vectors)

    return all_vectors