"""Offline Phase 7 coverage for generation contracts and safety boundaries."""

import asyncio

import pytest

from backend.ai.cache import QuestionCache, question_cache_key
from backend.ai.client import ProviderRequestError
from backend.ai.dedupe import hash_for_question
from backend.ai.exam import ExamGenerationError, generate_exam_questions
from backend.ai.schemas import QuestionDraft

CODE = "x = 1\nprint(x)"


def draft(prompt: str, *, line_refs=None) -> QuestionDraft:
    return QuestionDraft(
        type="design_decision",
        prompt=prompt,
        line_refs=line_refs or [1],
        answer_format="free_text",
        answer_key=None,
        rubric={
            "expected_points": ["Explains x"],
            "common_misconceptions": [],
            "scoring_guide": "Award relevant reasoning.",
        },
    )


class SequenceClient:
    def __init__(self, responses):
        self.responses, self.calls = iter(responses), 0

    async def generate_json(self, **_kwargs):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def run(*args, **kwargs):
    return asyncio.run(generate_exam_questions(*args, **kwargs))


def test_exam_combines_valid_deterministic_and_ai_questions(monkeypatch):
    deterministic = draft("Why is x initialized?")
    monkeypatch.setattr(
        "backend.ai.exam._deterministic_questions", lambda *_: [deterministic]
    )
    from backend.ai.exam import exam_cache

    exam_cache.clear()
    result = run(CODE, {}, 2, set(), client=SequenceClient([draft("Why print x?")]))
    assert [q.prompt for q in result] == [deterministic.prompt, "Why print x?"]
    assert all(
        1 <= line <= len(CODE.splitlines()) for q in result for line in q.line_refs
    )
    assert all(not hasattr(q, "private_answer_key") for q in result)


def test_invalid_and_duplicate_candidates_are_rejected_with_bounded_retries(
    monkeypatch,
):
    monkeypatch.setattr("backend.ai.exam._deterministic_questions", lambda *_: [])
    from backend.ai.exam import exam_cache

    exam_cache.clear()
    duplicate = draft("Known question")
    client = SequenceClient([duplicate, duplicate, draft("Bad line", line_refs=[99])])
    with pytest.raises(ExamGenerationError, match="within 3 attempts"):
        run(CODE, {}, 1, {hash_for_question(duplicate)}, client=client)
    assert client.calls == 3


def test_provider_failure_preserves_deterministic_fallback_and_signal(monkeypatch):
    monkeypatch.setattr(
        "backend.ai.exam._deterministic_questions", lambda *_: [draft("Deterministic")]
    )
    from backend.ai.exam import exam_cache

    exam_cache.clear()
    result = run(
        CODE, {}, 2, set(), client=SequenceClient([ProviderRequestError("offline")])
    )
    assert len(result) == 1 and result.used_fallback is True


def test_cache_isolated_and_returns_defensive_copies():
    cache = QuestionCache()
    first = question_cache_key(CODE, mode="exam", seed=42, compatibility={"count": 1})
    incompatible = question_cache_key(
        CODE, mode="exam", seed=42, compatibility={"count": 2}
    )
    practice = question_cache_key(
        CODE, mode="practice", seed=42, compatibility={"count": 1}
    )
    cache.set(first, [{"prompt": "original"}])
    received = cache.get(first)
    received[0]["prompt"] = "mutated"
    assert cache.get(first) == [{"prompt": "original"}]
    assert cache.get(incompatible) is None and cache.get(practice) is None
