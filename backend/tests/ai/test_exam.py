"""Offline contract tests for exam generation and its gateway boundary."""

import asyncio
import json
import sys
import types

import httpx
import pytest

import ai.exam as exam_module
from ai.client import OpenAICompatibleClient, ProviderRequestError
from ai.config import AIConfig
from ai.dedupe import hash_for_question
from ai.exam import ExamGenerationError, generate_exam_questions
from ai.schemas import QuestionDraft
from app.services import exam_generation_gateway


def draft(question_hash: str = "exam-hash", *, line_refs: list[int] | None = None):
    return QuestionDraft(
        type="design_decision",
        prompt=f"Why is this branch needed ({question_hash})?",
        line_refs=line_refs if line_refs is not None else [1],
        answer_format="free_text",
        rubric={
            "expected_points": ["Explains the branch"],
            "common_misconceptions": [],
            "scoring_guide": "Relevant explanation.",
        },
        question_hash=question_hash,
    )


class SequenceClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    async def generate_json(self, **kwargs):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def test_generates_exact_unique_schema_valid_questions():
    client = SequenceClient([draft("one"), draft("two")])

    result = asyncio.run(
        generate_exam_questions(
            "if ready:\n    run()", {"branches": 1}, 2, set(), client=client
        )
    )

    assert [question.question_hash for question in result] == [
        hash_for_question(draft("one")), hash_for_question(draft("two"))
    ]
    assert all(isinstance(question, QuestionDraft) for question in result)


def test_duplicate_and_invalid_candidates_are_bounded_and_rejected():
    client = SequenceClient([draft("known"), draft("known"), draft("bad", line_refs=[9])])

    with pytest.raises(ExamGenerationError, match="within 3 attempts"):
        asyncio.run(generate_exam_questions("x = 1", {}, 1, {hash_for_question(draft("known"))}, client=client))
    assert client.calls == 3


def test_provider_failure_is_not_routed_to_another_provider():
    client = SequenceClient([ProviderRequestError("grok unavailable")])

    with pytest.raises(ExamGenerationError, match="ProviderRequestError"):
        asyncio.run(generate_exam_questions("x = 1", {}, 1, set(), client=client))
    assert client.calls == 1


def test_live_exam_generation_uses_grok_request_configuration(monkeypatch):
    seen = {}

    async def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["model"] = json.loads(request.content)["model"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(draft("grok-one").model_dump())}}
                ]
            },
        )

    config = AIConfig(
        mode="live",
        xai_api_key="fake-xai-key",
        xai_base_url="https://grok.example/v1",
        xai_model="grok-test-model",
        agnes_api_key="fake-agnes-key",
        agnes_model="agnes-test-model",
    )
    client = OpenAICompatibleClient(
        provider="grok",
        base_url=config.xai_base_url,
        api_key="fake-xai-key",
        model=config.xai_model,
        transport=httpx.MockTransport(handler),
    )

    def factory(selected_config, *, task):
        assert selected_config is config
        assert task == "exam"
        return client

    monkeypatch.setattr("backend.ai.exam.create_ai_client", factory)
    result = asyncio.run(generate_exam_questions("x = 1", {}, 1, set(), config=config))
    asyncio.run(client.aclose())
    assert result[0].question_hash == hash_for_question(draft("grok-one"))
    assert seen == {
        "url": "https://grok.example/v1/chat/completions",
        "auth": "Bearer fake-xai-key",
        "model": "grok-test-model",
    }


def test_gateway_calls_exact_member3_contract(monkeypatch):
    captured = {}
    package = types.ModuleType("ai")
    module = types.ModuleType("ai.exam")

    async def implementation(*, code, facts, n, avoid_hashes):
        captured.update(code=code, facts=facts, n=n, avoid_hashes=avoid_hashes)
        return [draft("gateway")]

    module.generate_exam_questions = implementation
    monkeypatch.setitem(sys.modules, "ai", package)
    monkeypatch.setitem(sys.modules, "ai.exam", module)
    result = asyncio.run(
        exam_generation_gateway.generate_exam_questions("x = 1", {"x": 1}, 1, {"old"})
    )
    assert result[0].question_hash == "gateway"
    assert captured == {
        "code": "x = 1",
        "facts": {"x": 1},
        "n": 1,
        "avoid_hashes": {"old"},
    }


def test_deterministic_and_ai_mix_and_cache(monkeypatch):
    deterministic = draft("deterministic")
    ai = draft("ai")
    monkeypatch.setattr(exam_module, "_deterministic_questions", lambda code, facts, count: [deterministic])
    exam_module.exam_cache.clear()
    client = SequenceClient([ai])

    result = asyncio.run(generate_exam_questions("x = 1", {}, 2, set(), client=client))
    cached = asyncio.run(generate_exam_questions("x = 1", {}, 2, set(), client=SequenceClient([])))

    assert [item.question_hash for item in result] == [hash_for_question(deterministic), hash_for_question(ai)]
    assert [item.question_hash for item in cached] == [hash_for_question(deterministic), hash_for_question(ai)]
    assert client.calls == 1


def test_provider_failure_preserves_deterministic_fallback(monkeypatch):
    deterministic = draft("deterministic-only")
    monkeypatch.setattr(exam_module, "_deterministic_questions", lambda code, facts, count: [deterministic])
    exam_module.exam_cache.clear()

    result = asyncio.run(
        generate_exam_questions(
            "x = 1", {}, 2,
            set(), client=SequenceClient([ProviderRequestError("offline")]),
        )
    )

    assert [item.question_hash for item in result] == [hash_for_question(deterministic)]
    assert result.used_fallback is True
