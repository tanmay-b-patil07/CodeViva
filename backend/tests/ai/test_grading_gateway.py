"""Offline contract tests for the Grok-routed grading gateway."""

import asyncio
import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from backend.ai.client import OpenAICompatibleClient
from backend.ai.config import AIConfig
from backend.ai.schemas import JudgeOutput
from backend.app.schemas.grading import (
    GradingAnswerInput,
    GradingAttemptInput,
    GradingQuestionInput,
)
from backend.app.services.grading_gateway import GradingGatewayError, grade_attempt


def payload(
    *,
    answer: str | None = "The condition protects the branch.",
    max_score: Decimal = Decimal(5),
):
    question_id = uuid4()
    return GradingAttemptInput(
        attempt_id=uuid4(),
        student_id=uuid4(),
        slot_id=uuid4(),
        questions=[
            GradingQuestionInput(
                id=question_id,
                prompt="Why is this branch needed?",
                type="design_decision",
                answer_format="free_text",
                answer_key={"expected": "guard invalid state"},
                rubric={"scoring_guide": "Award relevant explanation."},
                max_score=max_score,
                answer=(
                    GradingAnswerInput(question_id=question_id, answer_text=answer)
                    if answer is not None
                    else None
                ),
            )
        ],
    )


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    async def generate_json(self, **_kwargs):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_gateway_contract_generates_server_bound_result():
    attempt = payload()
    client = FakeClient(
        JudgeOutput(
            score=4, evidence="Relevant", confidence=0.5, feedback="Good explanation."
        )
    )

    result = asyncio.run(grade_attempt(attempt, client=client))

    assert result.attempt_id == attempt.attempt_id
    assert result.total_score == result.question_grades[0].awarded_score == Decimal(4)
    assert result.max_score == result.question_grades[0].max_score == Decimal(5)
    assert result.question_grades[0].question_id == attempt.questions[0].id
    assert result.question_grades[0].needs_review is True
    assert client.calls == 1


def test_unanswered_question_is_zero_without_provider_request():
    attempt = payload(answer=None)
    client = FakeClient(AssertionError("provider must not be used"))

    result = asyncio.run(grade_attempt(attempt, client=client))

    assert result.total_score == Decimal(0)
    assert result.question_grades[0].feedback == "No answer was submitted."
    assert client.calls == 0


def test_invalid_score_and_provider_error_fail_safely():
    attempt = payload()
    too_high = FakeClient(
        JudgeOutput(score=6, evidence="x", confidence=1, feedback="x")
    )
    with pytest.raises(GradingGatewayError, match="above"):
        asyncio.run(grade_attempt(attempt, client=too_high))

    broken = FakeClient(RuntimeError("provider details"))
    with pytest.raises(GradingGatewayError, match="RuntimeError"):
        asyncio.run(grade_attempt(attempt, client=broken))


def test_mock_mode_never_constructs_network_client():
    attempt = payload(max_score=Decimal(10))
    result = asyncio.run(
        grade_attempt(attempt, config=AIConfig(mode="mock", xai_api_key="present"))
    )
    assert result.total_score == Decimal(8)


def test_live_grading_uses_grok_endpoint_and_model(monkeypatch):
    seen = {}

    async def handler(request):
        seen["url"] = str(request.url)
        seen["model"] = json.loads(request.content)["model"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "score": 3,
                                    "evidence": "supported",
                                    "confidence": 0.9,
                                    "feedback": "Solid.",
                                }
                            )
                        }
                    }
                ]
            },
        )

    config = AIConfig(
        mode="live",
        xai_api_key="fake",
        xai_base_url="https://grok.test/v1",
        xai_model="grok-test",
    )
    client = OpenAICompatibleClient(
        provider="grok",
        base_url=config.xai_base_url,
        api_key="fake",
        model="grok-test",
        transport=httpx.MockTransport(handler),
    )
    monkeypatch.setattr(
        "backend.ai.evaluator.create_ai_client", lambda selected, *, task: client
    )
    result = asyncio.run(grade_attempt(payload(), config=config))
    asyncio.run(client.aclose())

    assert result.total_score == Decimal(3)
    assert seen == {
        "url": "https://grok.test/v1/chat/completions",
        "model": "grok-test",
    }
