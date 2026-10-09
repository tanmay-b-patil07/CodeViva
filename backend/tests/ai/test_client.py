"""Offline tests for the CodeViva AI foundation."""

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from ai.client import (
    InvalidAIResponseError,
    MockLLMClient,
    OpenAICompatibleClient,
    ProviderNotConfiguredError,
    ProviderRequestError,
    chat_completions_url,
    create_ai_client,
    load_prompt,
)
from ai.config import AIConfig
from ai.schemas import JudgeOutput, QuestionDraft, Score


def test_mock_client_generates_valid_question():
    async def run():
        client = MockLLMClient()
        result = await client.generate_json(
            system_prompt="Follow the system rules.",
            user_prompt="Create a question about the code.",
            response_model=QuestionDraft,
        )
        assert isinstance(result, QuestionDraft)
        assert result.line_refs == [1]
        assert result.rubric is not None

    asyncio.run(run())


def test_mock_client_generates_valid_judgement():
    async def run():
        result = await MockLLMClient().generate_json(
            system_prompt="Judge fairly.",
            user_prompt="Evaluate the sample answer.",
            response_model=JudgeOutput,
        )
        assert result.score == 8
        assert 0 <= result.confidence <= 1

    asyncio.run(run())


def test_mock_is_the_default_provider(monkeypatch):
    monkeypatch.delenv("CODEVIVA_AI_PROVIDER", raising=False)
    config = AIConfig.from_env()
    assert config.provider == "mock"
    assert isinstance(create_ai_client(config), MockLLMClient)


def test_unimplemented_provider_fails_clearly():
    config = AIConfig(provider="unselected-provider")
    with pytest.raises(ProviderNotConfiguredError):
        create_ai_client(config)


def test_provider_defaults_and_overrides(monkeypatch):
    for name in (
        "CODEVIVA_AI_PROVIDER_PRACTICE",
        "CODEVIVA_AI_PROVIDER_EXAM",
        "CODEVIVA_AI_PROVIDER_GRADING",
        "CODEVIVA_AI_MODE",
    ):
        monkeypatch.delenv(name, raising=False)
    config = AIConfig.from_env()
    assert (
        config.provider_for("practice"),
        config.provider_for("exam"),
        config.provider_for("grading"),
    ) == ("agnes", "grok", "grok")
    monkeypatch.setenv("CODEVIVA_AI_PROVIDER_PRACTICE", "grok")
    assert AIConfig.from_env().provider_for("practice") == "grok"


def test_live_routing_selects_credentials_models_and_endpoint():
    config = AIConfig(
        mode="live",
        agnes_api_key="agnes-test",
        xai_api_key="xai-test",
        agnes_model="agnes-model",
        xai_model="grok-model",
    )
    practice = create_ai_client(config, task="practice")
    exam = create_ai_client(config, task="exam")
    grading = create_ai_client(config, task="grading")
    assert isinstance(practice, OpenAICompatibleClient)
    assert (practice.provider, practice.model, practice.endpoint) == (
        "agnes",
        "agnes-model",
        "https://apihub.agnes-ai.com/v1/chat/completions",
    )
    assert (exam.provider, exam.model, grading.provider) == (
        "grok",
        "grok-model",
        "grok",
    )
    assert (
        chat_completions_url("https://example.test/v1/chat/completions/")
        == "https://example.test/v1/chat/completions"
    )


def test_live_mode_requires_credential():
    with pytest.raises(ProviderNotConfiguredError, match="API key"):
        create_ai_client(AIConfig(mode="live", agnes_model="a"), task="practice")


def test_provider_models_override_legacy_models():
    config = AIConfig(
        model_practice="legacy-practice",
        model_exam="legacy-exam",
        agnes_model="agnes-model",
        xai_model="grok-model",
    )
    assert config.model_for("practice") == "agnes-model"
    assert config.model_for("exam") == "grok-model"
    assert config.model_for("grading") == "grok-model"


def test_legacy_models_are_fallbacks_when_provider_model_is_unset():
    config = AIConfig(model_practice="legacy-practice", model_exam="legacy-exam")
    assert config.model_for("practice") == "legacy-practice"
    assert config.model_for("exam") == "legacy-exam"
    assert config.model_for("grading") is None


def test_live_mode_requires_selected_provider_model():
    with pytest.raises(ProviderNotConfiguredError, match="model for practice"):
        create_ai_client(AIConfig(mode="live", agnes_api_key="fake"), task="practice")


def test_mock_mode_never_constructs_network_client():
    assert isinstance(
        create_ai_client(AIConfig(mode="mock", agnes_api_key="present")), MockLLMClient
    )


def test_openai_compatible_parses_schema_and_uses_safe_request():
    seen = {}

    async def handler(request):
        seen["url"], seen["authorization"], seen["body"] = (
            str(request.url),
            request.headers["authorization"],
            json.loads(request.content),
        )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "score": 7,
                                    "evidence": "supported",
                                    "confidence": 0.8,
                                    "feedback": "good",
                                }
                            )
                        }
                    }
                ]
            },
        )

    async def run():
        client = OpenAICompatibleClient(
            provider="grok",
            base_url="https://fake.test/v1",
            api_key="fake-key",
            model="fake-model",
            transport=httpx.MockTransport(handler),
        )
        result = await client.generate_json(
            system_prompt="system", user_prompt="user", response_model=JudgeOutput
        )
        await client.aclose()
        assert result.score == 7

    asyncio.run(run())
    assert seen["url"].endswith("/v1/chat/completions")
    assert seen["authorization"] == "Bearer fake-key"
    assert seen["body"]["model"] == "fake-model"


@pytest.mark.parametrize(
    "content,error",
    [
        ("not-json", InvalidAIResponseError),
        ("", InvalidAIResponseError),
        (json.dumps({"score": 99}), InvalidAIResponseError),
    ],
)
def test_invalid_or_empty_provider_content_is_rejected(content, error):
    async def handler(request):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": content}}]}
        )

    async def run():
        client = OpenAICompatibleClient(
            provider="agnes",
            base_url="https://fake.test/v1",
            api_key="fake",
            model="fake",
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(error):
            await client.generate_json(
                system_prompt="s", user_prompt="u", response_model=JudgeOutput
            )
        await client.aclose()

    asyncio.run(run())


def test_non_retryable_and_retryable_errors_are_bounded():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429 if calls < 3 else 500, json={})

    async def run():
        client = OpenAICompatibleClient(
            provider="grok",
            base_url="https://fake.test/v1",
            api_key="secret-value",
            model="fake",
            max_retries=2,
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(ProviderRequestError) as exc:
            await client.generate_json(
                system_prompt="s", user_prompt="u", response_model=JudgeOutput
            )
        await client.aclose()
        assert "secret-value" not in str(exc.value)

    asyncio.run(run())
    assert calls == 3


def test_authentication_failure_is_not_retried():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={})

    async def run():
        client = OpenAICompatibleClient(
            provider="grok",
            base_url="https://fake.test/v1",
            api_key="fake",
            model="fake",
            max_retries=3,
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(ProviderRequestError, match="HTTP 401"):
            await client.generate_json(
                system_prompt="s", user_prompt="u", response_model=JudgeOutput
            )
        await client.aclose()

    asyncio.run(run())
    assert calls == 1


def test_timeout_is_retried_only_to_configured_bound():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout", request=request)

    async def run():
        client = OpenAICompatibleClient(
            provider="agnes",
            base_url="https://fake.test/v1",
            api_key="fake",
            model="fake",
            max_retries=1,
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(ProviderRequestError, match="timeout"):
            await client.generate_json(
                system_prompt="s", user_prompt="u", response_model=JudgeOutput
            )
        await client.aclose()

    asyncio.run(run())
    assert calls == 2


def test_prompt_loader_reads_system_prompt():
    prompt = load_prompt("system_base.txt")
    assert "Ground every claim" in prompt


def test_prompt_loader_rejects_path_traversal():
    with pytest.raises(ValueError):
        load_prompt("../.env")


def test_score_rejects_score_above_maximum():
    with pytest.raises(ValidationError):
        Score(
            question_id="db-question-uuid",
            max_score=10,
            score=11,
            evidence="Sample evidence",
            confidence=0.9,
            needs_review=False,
            feedback="Sample feedback",
        )
