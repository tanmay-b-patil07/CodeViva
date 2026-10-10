from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.errors import AppError
from app.services import ai_assignment_service


def test_code_assessment_validates_review_and_private_question_shape(monkeypatch):
    monkeypatch.setattr(
        ai_assignment_service,
        "_request_json",
        lambda **_kwargs: {
            "code_review": {
                "summary": "The function is clear.",
                "code_suggestions": ["Handle an empty input explicitly."],
                "understanding_suggestions": ["Trace one loop iteration by hand."],
            },
            "questions": [
                {
                    "prompt": "What does the loop accumulate?",
                    "expected_answer": "The sum of even values.",
                    "rubric": "Award credit for identifying the condition and sum.",
                    "line_refs": [2],
                    "max_score": 5,
                }
            ],
        },
    )

    result = ai_assignment_service.analyze_assignment_code(
        code="def total(values):\n    return sum(values)",
        language="python",
        title="Loop reasoning",
        instructions=None,
        code_facts={"language": "python"},
        generate_questions=True,
    )

    assert result.code_review.code_suggestions == [
        "Handle an empty input explicitly."
    ]
    assert result.questions[0].expected_answer == "The sum of even values."
    assert result.questions[0].max_score == Decimal(5)


def test_code_assessment_rejects_question_references_outside_source(monkeypatch):
    monkeypatch.setattr(
        ai_assignment_service,
        "_request_json",
        lambda **_kwargs: {
            "code_review": {
                "summary": "Review",
                "code_suggestions": ["Improve naming."],
                "understanding_suggestions": ["Trace the return value."],
            },
            "questions": [
                {
                    "prompt": "Question",
                    "expected_answer": "Answer",
                    "rubric": "Criteria",
                    "line_refs": [10],
                    "max_score": 5,
                }
            ],
        },
    )

    with pytest.raises(AppError, match="invalid source line references"):
        ai_assignment_service.analyze_assignment_code(
            code="print('hello')",
            language="python",
            title="Practice",
            instructions=None,
            code_facts={"language": "python"},
            generate_questions=True,
        )


def test_attempt_grade_rejects_scores_above_question_maximum(monkeypatch):
    monkeypatch.setattr(
        ai_assignment_service,
        "_request_json",
        lambda **_kwargs: {
            "evaluations": [
                {
                    "question_id": "q-1",
                    "score": 6,
                    "confidence": 0.9,
                    "evidence": "The student identified the loop.",
                    "feedback": "Explain the loop condition more precisely.",
                }
            ]
        },
    )

    with pytest.raises(AppError, match="above the question maximum"):
        ai_assignment_service.evaluate_attempt(
            source_code="for value in values: pass",
            language="python",
            answers=[
                {
                    "question_id": "q-1",
                    "prompt": "Explain the loop.",
                    "answer_text": "It iterates over values.",
                    "expected_answer": {"expected_answer": "Iterates"},
                    "rubric": {"criteria": "Identify the sequence"},
                    "max_score": "5",
                }
            ],
        )


def test_attempt_grade_requires_one_result_per_question(monkeypatch):
    monkeypatch.setattr(
        ai_assignment_service,
        "_request_json",
        lambda **_kwargs: {"evaluations": []},
    )

    with pytest.raises(AppError, match="did not grade each answer exactly once"):
        ai_assignment_service.evaluate_attempt(
            source_code="print('hello')",
            language="python",
            answers=[
                {
                    "question_id": "q-1",
                    "prompt": "What is printed?",
                    "answer_text": "hello",
                    "expected_answer": {"expected_answer": "hello"},
                    "rubric": {"criteria": "Correct output"},
                    "max_score": "1",
                }
            ],
        )


def test_request_json_uses_agnes_openai_compatible_chat_api(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        ai_assignment_service.settings,
        "agnes_api_key",
        "test-agnes-key",
    )
    monkeypatch.setattr(
        ai_assignment_service.settings,
        "agnes_api_base_url",
        "https://api.example.test/v1/",
    )

    def fake_post(url, *, headers, json, timeout):
        captured.update(
            url=url,
            headers=headers,
            json=json,
            timeout=timeout,
        )
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {"message": {"content": '{"result": "ok"}'}}
                ]
            },
        )

    monkeypatch.setattr(ai_assignment_service.httpx, "post", fake_post)

    result = ai_assignment_service._request_json(
        system="Be precise.",
        payload={"code": "print(1)"},
        max_tokens=400,
        model="agnes-2.5-flash",
    )

    assert result == {"result": "ok"}
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-agnes-key"
    assert captured["json"]["model"] == "agnes-2.5-flash"
    assert captured["json"]["messages"][0] == {
        "role": "system",
        "content": "Be precise.",
    }


def test_request_json_requires_agnes_api_key(monkeypatch):
    monkeypatch.setattr(ai_assignment_service.settings, "agnes_api_key", "")

    with pytest.raises(AppError, match="Agnes AI is not configured"):
        ai_assignment_service._request_json(
            system="Be precise.",
            payload={},
            max_tokens=10,
            model="agnes-2.5-flash",
        )


def test_request_json_parses_agnes_markdown_json_fence(monkeypatch):
    monkeypatch.setattr(ai_assignment_service.settings, "agnes_api_key", "test-agnes-key")
    monkeypatch.setattr(
        ai_assignment_service.httpx,
        "post",
        lambda *_args, **_kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"result": "ok"}\n```'
                        }
                    }
                ]
            },
        ),
    )

    result = ai_assignment_service._request_json(
        system="Be precise.",
        payload={},
        max_tokens=10,
        model="agnes-2.5-flash",
    )

    assert result == {"result": "ok"}
