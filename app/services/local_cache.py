import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None

        expires_at, value = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self.max_items:
            self._evict_oldest()

        self._store[key] = (time.time() + self.ttl_seconds, value)

    def _evict_oldest(self) -> None:
        if not self._store:
            return

        oldest_key = min(self._store.items(), key=lambda item: item[1][0])[0]
        self._store.pop(oldest_key, None)