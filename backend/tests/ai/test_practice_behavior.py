"""Behavior tests for practice question generation."""

import asyncio
import json
import sys
import types

import httpx
import pytest
from pydantic import BaseModel

from backend.ai.client import OpenAICompatibleClient, ProviderRequestError
from backend.ai.config import AIConfig
from backend.ai.dedupe import hash_for_question
from backend.ai.practice import (
    PracticeGenerationError,
    _question_hash,
    _to_private_question,
    stream_practice_questions,
)
from backend.ai.schemas import QuestionDraft


class FakeCodeFacts(BaseModel):
    line_count: int = 2


class FakePrivateQuestion(BaseModel):
    id: str
    type: str
    prompt: str
    line_refs: list[int]
    answer_format: str
    options: list[str] | None = None
    max_score: float = 10
    answer_key: str | dict | None = None
    rubric: dict | None = None
    explanation: str | None = None
    question_hash: str | None = None


class FakeClient:
    def __init__(self, drafts):
        self.drafts = iter(drafts)

    async def generate_json(self, *, system_prompt, user_prompt, response_model):
        return next(self.drafts)


def install_fake_analysis(
    monkeypatch,
    deterministic_questions,
    trace_options: dict | None = None,
):
    """Install fakes matching Member 2's documented public interface."""
    package = types.ModuleType("backend.analysis")
    package.__path__ = []

    models = types.ModuleType("backend.analysis.models")
    models.CodeFacts = FakeCodeFacts
    models.QuestionPrivate = FakePrivateQuestion

    questions = types.ModuleType("backend.analysis.questions")

    def build_deterministic_questions(
        code,
        facts,
        n,
        seed,
        *,
        allow_in_process_trace=True,
    ):
        if trace_options is not None:
            trace_options["allow_in_process_trace"] = allow_in_process_trace
        return deterministic_questions[:n]

    questions.build_deterministic_questions = build_deterministic_questions

    validator = types.ModuleType("backend.analysis.validator")
    validator.validate_question = lambda q, code, facts: []

    monkeypatch.setitem(sys.modules, "backend.analysis", package)
    monkeypatch.setitem(sys.modules, "backend.analysis.models", models)
    monkeypatch.setitem(sys.modules, "backend.analysis.questions", questions)
    monkeypatch.setitem(sys.modules, "backend.analysis.validator", validator)


def deterministic_question():
    return FakePrivateQuestion(
        id="deterministic-1",
        type="trace_output",
        prompt="What does this function return?",
        line_refs=[2],
        answer_format="short_text",
        answer_key="2",
        question_hash="deterministic-hash",
    )


def ai_draft(prompt, line_refs=None):
    return QuestionDraft(
        type="design_decision",
        prompt=prompt,
        line_refs=line_refs if line_refs is not None else [1],
        answer_format="free_text",
        answer_key=None,
        rubric={
            "expected_points": ["Explains the code-specific choice"],
            "common_misconceptions": [],
            "scoring_guide": "Award credit for a relevant explanation.",
        },
        explanation="Practice explanation.",
    )


def test_deterministic_question_is_yielded_first(monkeypatch):
    install_fake_analysis(monkeypatch, [deterministic_question()])
    client = FakeClient([ai_draft("Why is this function used?")])

    async def run():
        return [
            q
            async for q in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                client=client,
                total_questions=2,
            )
        ]

    results = asyncio.run(run())

    assert len(results) == 2
    assert results[0].type == "trace_output"
    assert results[1].type == "design_decision"


def test_invalid_line_reference_is_rejected(monkeypatch):
    install_fake_analysis(monkeypatch, [])
    client = FakeClient([ai_draft("Explain this code", [99]) for _ in range(8)])

    async def run():
        return [
            q
            async for q in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                client=client,
                total_questions=1,
            )
        ]

    with pytest.raises(PracticeGenerationError):
        asyncio.run(run())


def test_duplicate_ai_questions_are_not_yielded(monkeypatch):
    install_fake_analysis(monkeypatch, [])
    draft = ai_draft("Why is this function used?")
    client = FakeClient([draft] * 8)

    async def run():
        return [
            q
            async for q in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                client=client,
                total_questions=2,
            )
        ]

    results = asyncio.run(run())

    assert len(results) == 1
    assert results[0].type == "design_decision"


def test_saved_hashes_are_skipped_when_resuming(monkeypatch):
    install_fake_analysis(monkeypatch, [deterministic_question()])
    client = FakeClient([ai_draft("Why is this function used?")])

    async def run():
        return [
            q
            async for q in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                client=client,
                total_questions=1,
                    avoid_hashes={hash_for_question(deterministic_question())},
            )
        ]

    results = asyncio.run(run())

    assert len(results) == 1
    assert results[0].type == "design_decision"
    assert results[0].question_hash != "deterministic-hash"


def test_mock_mode_practice_runs_offline_with_credentials_present(monkeypatch):
    install_fake_analysis(monkeypatch, [])
    config = AIConfig(
        mode="mock",
        agnes_api_key="fake-agnes-key",
        agnes_model="agnes-test-model",
    )

    async def run():
        return [
            question
            async for question in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                config=config,
                total_questions=1,
            )
        ]

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].type == "design_decision"


def test_live_practice_uses_agnes_endpoint_model_and_credentials(monkeypatch):
    """Practice selects its configured provider; MockTransport blocks network I/O."""
    install_fake_analysis(monkeypatch, [])
    seen = {}

    async def handler(request):
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers["authorization"]
        seen["model"] = json.loads(request.content)["model"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                ai_draft("Why is this function used?").model_dump()
                            )
                        }
                    }
                ]
            },
        )

    client = OpenAICompatibleClient(
        provider="agnes",
        base_url="https://agnes.example/v1",
        api_key="fake-agnes-key",
        model="agnes-test-model",
        transport=httpx.MockTransport(handler),
    )
    config = AIConfig(
        mode="live",
        agnes_api_key="fake-agnes-key",
        agnes_base_url="https://agnes.example/v1",
        agnes_model="agnes-test-model",
        xai_api_key="fake-xai-key",
        xai_model="xai-test-model",
    )

    def factory(selected_config, *, task):
        assert selected_config is config
        assert task == "practice"
        return client

    monkeypatch.setattr("backend.ai.practice.create_ai_client", factory)

    async def run():
        return [
            question
            async for question in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                config=config,
                total_questions=1,
            )
        ]

    results = asyncio.run(run())
    asyncio.run(client.aclose())
    assert len(results) == 1
    assert seen == {
        "url": "https://agnes.example/v1/chat/completions",
        "authorization": "Bearer fake-agnes-key",
        "model": "agnes-test-model",
    }


def test_live_practice_failure_does_not_fallback_to_another_provider(monkeypatch):
    install_fake_analysis(monkeypatch, [])
    config = AIConfig(mode="live", agnes_api_key="fake", agnes_model="agnes")
    factory_calls = []

    class FailingAgnesClient:
        async def generate_json(self, **kwargs):
            raise ProviderRequestError("agnes request failed")

    def factory(selected_config, *, task):
        factory_calls.append((selected_config.provider_for(task), task))
        return FailingAgnesClient()

    monkeypatch.setattr("backend.ai.practice.create_ai_client", factory)

    async def run():
        return [
            question
            async for question in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                config=config,
                total_questions=1,
            )
        ]

    with pytest.raises(PracticeGenerationError):
        asyncio.run(run())
    assert factory_calls == [("agnes", "practice")]


def test_private_practice_question_uses_member2_sha1_hash():
    from backend.analysis.models import CodeFacts, QuestionPrivate
    from backend.analysis.validator import validate_question

    draft = ai_draft("Why is this function used?")
    question = _to_private_question(draft, QuestionPrivate)

    assert question.question_hash == _question_hash(draft)
    assert question.question_hash.startswith("sha1:")
    assert validate_question(
        question,
        "def f():\n    return 2",
        CodeFacts(line_count=2, language="python", code_hash="sha256:test"),
    ) == []


def test_member2_validator_rejects_incorrect_question_hash():
    from backend.analysis.models import CodeFacts, QuestionPrivate
    from backend.analysis.validator import validate_question

    draft = ai_draft("Why is this function used?")
    question = _to_private_question(draft, QuestionPrivate).model_copy(
        update={"question_hash": "sha256:incorrect"}
    )

    problems = validate_question(
        question,
        "def f():\n    return 2",
        CodeFacts(line_count=2, language="python", code_hash="sha256:test"),
    )
    assert "Question hash does not match question content." in problems


def test_dictionary_answer_key_is_rejected_at_member2_boundary():
    from backend.analysis.models import QuestionPrivate

    draft = ai_draft("Why is this function used?")
    draft.answer_key = {"expected": "an explanation"}

    with pytest.raises(PracticeGenerationError, match="Dictionary answer keys"):
        _to_private_question(draft, QuestionPrivate)


def test_practice_disables_in_process_tracing_for_submitted_code(monkeypatch):
    trace_options = {}
    install_fake_analysis(monkeypatch, [], trace_options)
    client = FakeClient([ai_draft("Why is this function used?")])

    async def run():
        return [
            question
            async for question in stream_practice_questions(
                "def f():\n    return 2",
                FakeCodeFacts(),
                client=client,
                total_questions=1,
            )
        ]

    assert asyncio.run(run())
    assert trace_options == {"allow_in_process_trace": False}
