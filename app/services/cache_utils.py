import hashlib


def text_cache_key(text: str) -> str:
    normalized = (text or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()