"""Bounded, process-local question-batch cache.

The documented identity starts with ``(code_hash, mode, seed)``. A canonical
compatibility payload is deliberately included as a fourth component so a
different count, facts, or exclusion set cannot reuse an incompatible batch.
"""

import hashlib
import json
from collections import OrderedDict
from copy import deepcopy
from typing import Any


def code_hash(code: str) -> str:
    """Return the stable content hash used by all question-cache callers."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def question_cache_key(
    code: str, *, mode: str, seed: int, compatibility: dict[str, Any] | None = None
) -> tuple[str, str, int, str]:
    """Build a deterministic, mode-isolated cache key without retaining code."""
    if mode not in {"practice", "exam"}:
        raise ValueError("mode must be practice or exam")
    payload = json.dumps(
        compatibility or {}, sort_keys=True, separators=(",", ":"), default=str
    )
    return (code_hash(code), mode, seed, payload)


class QuestionCache:
    """LRU cache that never exposes a mutable stored object to callers."""
    def __init__(self, max_entries: int = 128) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self.max_entries = max_entries
        self._entries: OrderedDict[tuple[str, str, int, str], Any] = OrderedDict()

    def get(self, key: tuple[str, str, int, str]) -> Any | None:
        value = self._entries.get(key)
        if value is None:
            return None
        self._entries.move_to_end(key)
        return deepcopy(value)

    def set(self, key: tuple[str, str, int, str], value: Any) -> None:
        self._entries[key] = deepcopy(value)
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


# Backwards-compatible name retained for the Phase 3 exam integration.
ExamQuestionCache = QuestionCache
exam_cache = QuestionCache()
# A single bounded store is safe because ``mode`` is part of every key.
question_cache = exam_cache
