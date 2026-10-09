"""Member 2-compatible question hashing and defensive duplicate filtering."""

import hashlib
import json
from collections.abc import Iterable
from typing import Any


def question_hash(*, question_type: str, prompt: str, line_refs: list[int]) -> str:
    raw = json.dumps({"type": question_type, "prompt": prompt, "line_refs": line_refs}, sort_keys=True)
    return "sha1:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()


def hash_for_question(question: Any) -> str:
    """Derive a content hash, tolerating absent or malformed supplied hashes."""
    get = question.get if isinstance(question, dict) else lambda name: getattr(question, name, None)
    refs = get("line_refs")
    if not isinstance(refs, (list, tuple)):
        refs = []
    # Do not trust a provider-supplied hash: persistence requires this contract.
    return question_hash(
        question_type=str(get("type") or ""),
        prompt=str(get("prompt") or ""),
        line_refs=[reference for reference in refs if isinstance(reference, int)],
    )


def unique_questions(questions: Iterable[Any], avoid_hashes: set[str] | None = None) -> list[Any]:
    """Keep first content-unique questions while preserving valid candidates."""
    seen = {value for value in (avoid_hashes or set()) if isinstance(value, str) and value}
    result = []
    for question in questions:
        try:
            value = hash_for_question(question)
        except (TypeError, ValueError):
            # A malformed object should not prevent later valid candidates.
            continue
        if value not in seen:
            seen.add(value)
            result.append(question)
    return result
