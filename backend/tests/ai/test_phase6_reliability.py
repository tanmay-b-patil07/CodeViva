"""Offline Phase 6 reliability tests; all provider boundaries are fakes."""

import asyncio

import pytest

import ai.exam as exam_module
from ai.cache import QuestionCache, question_cache_key
from ai.config import AIConfig
from ai.dedupe import hash_for_question, unique_questions
from ai.exam import ExamGenerationError, generate_exam_questions
from ai.schemas import QuestionDraft


def draft(prompt: str) -> QuestionDraft:
    return QuestionDraft(
        type="design_decision", prompt=prompt, line_refs=[1], answer_format="free_text",
        rubric={"expected_points": ["reason"], "common_misconceptions": [], "scoring_guide": "reasoned"},
    )


class Client:
    def __init__(self, responses, delay=0):
        self.responses = iter(responses)
        self.delay = delay
        self.calls = 0
        self.active = 0
        self.maximum = 0

    async def generate_json(self, **_kwargs):
        self.calls += 1
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            item = next(self.responses)
            if isinstance(item, Exception):
                raise item
            return item
        finally:
            self.active -= 1


def test_cache_key_is_deterministic_mode_isolated_and_values_are_copied():
    exam_key = question_cache_key("x = 1", mode="exam", seed=42, compatibility={"question_count": 1})
    assert exam_key == question_cache_key("x = 1", mode="exam", seed=42, compatibility={"question_count": 1})
    assert exam_key != question_cache_key("x = 1", mode="practice", seed=42, compatibility={"question_count": 1})
    assert exam_key != question_cache_key("x = 1", mode="exam", seed=42, compatibility={"question_count": 2})
    cache = QuestionCache(1)
    cache.set(exam_key, {"questions": [{"prompt": "a"}]})
    received = cache.get(exam_key)
    received["questions"][0]["prompt"] = "mutated"
    assert cache.get(exam_key)["questions"][0]["prompt"] == "a"
    cache.set(question_cache_key("y = 1", mode="exam", seed=42), {"questions": []})
    assert cache.get(exam_key) is None


def test_cached_question_mutation_cannot_change_a_later_read():
    key = question_cache_key("x = 1", mode="exam", seed=42)
    cache = QuestionCache()
    cache.set(key, {"questions": [draft("Private answer")]})
    first = cache.get(key)
    first["questions"][0].prompt = "Changed by caller"
    assert cache.get(key)["questions"][0].prompt == "Private answer"


def test_shared_hashing_deduplicates_malformed_provider_hashes_and_history():
    first = draft("Why this branch?").model_copy(update={"question_hash": "not-a-contract-hash"})
    duplicate = draft("Why this branch?").model_copy(update={"question_hash": None})
    other = draft("Why this loop?")
    assert unique_questions([first, duplicate, other], {hash_for_question(first)}) == [other]


def test_exam_concurrency_is_bounded_and_metadata_is_safe(monkeypatch):
    exam_module.exam_cache.clear()
    monkeypatch.setattr(exam_module, "_deterministic_questions", lambda *_args: [])
    client = Client([draft(f"Question {index}") for index in range(4)], delay=0.02)
    config = AIConfig(exam_max_concurrency=2)

    async def run():
        return await asyncio.gather(*[
            generate_exam_questions(f"x = {index}", {}, 1, set(), client=client, config=config)
            for index in range(4)
        ])

    results = asyncio.run(run())
    assert client.maximum == 2
    assert all(batch.metadata["cache"] == "miss" and batch.metadata["attempts"] == 1 for batch in results)
    assert all("usage" not in batch.metadata for batch in results)


def test_exam_permit_is_released_after_provider_error(monkeypatch):
    exam_module.exam_cache.clear()
    monkeypatch.setattr(exam_module, "_deterministic_questions", lambda *_args: [])
    config = AIConfig(exam_max_concurrency=1)
    with pytest.raises(ExamGenerationError):
        asyncio.run(generate_exam_questions("bad", {}, 1, set(), client=Client([TimeoutError()]), config=config))
    result = asyncio.run(generate_exam_questions("good", {}, 1, set(), client=Client([draft("Recovered")]), config=config))
    assert result[0].question_hash == hash_for_question(draft("Recovered"))
