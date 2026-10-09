"""Member 1 boundary for Member 3 exam-question generation."""

import inspect
from typing import Any


async def generate_exam_questions(
    code: str,
    facts: dict[str, Any],
    n: int,
    avoid_hashes: set[str],
) -> list[Any]:
    """Call Member 3's implementation without owning or replacing it."""
    try:
        from ai.exam import generate_exam_questions as member3_generate
    except (ImportError, AttributeError) as exc:
        raise RuntimeError("Member 3 exam generation is not available.") from exc

    result = member3_generate(
        code=code,
        facts=facts,
        n=n,
        avoid_hashes=avoid_hashes,
    )
    if inspect.isawaitable(result):
        result = await result
    # Preserve list compatibility and the optional server-side fallback flag.
    return result if isinstance(result, list) else list(result)
