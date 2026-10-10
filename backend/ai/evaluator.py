"""Per-question answer evaluation using the shared grading client.

``evaluate_answer(question, answer, question_id, ...)`` returns the shared
``Score`` model.  It is intentionally independent of the application-level
attempt gateway, whose stable input/output models differ from ``QuestionDraft``.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any

from .client import LLMClient, create_ai_client
from .config import AIConfig, load_prompt
from .schemas import JudgeOutput, QuestionDraft, Score


class EvaluationError(RuntimeError):
    """A safe evaluator failure that callers must surface as failed/review."""


_STOP_WORDS = {"a", "an", "the", "and", "is", "it", "of", "to", "this"}


def _normalise(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold()).split())


def _answer_key(value: str | dict[str, Any] | None) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("answer", "value", "expected", "correct"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
    return None


def _result(
    question: QuestionDraft,
    question_id: str,
    score: float,
    evidence: str,
    confidence: float,
    needs_review: bool,
    feedback: str,
) -> Score:
    return Score(
        question_id=question_id,
        max_score=question.max_score,
        score=min(max(score, 0), question.max_score),
        evidence=evidence,
        confidence=confidence,
        needs_review=needs_review,
        feedback=feedback,
    )


def _grade_deterministic(
    question: QuestionDraft, answer: str, question_id: str
) -> Score:
    key = _answer_key(question.answer_key)
    if not key:
        raise EvaluationError("Deterministic question has no usable answer key")
    submitted, expected = _normalise(answer), _normalise(key)
    if question.answer_format == "numeric":
        try:
            correct = Decimal(answer.strip()) == Decimal(key.strip())
        except InvalidOperation:
            correct = False
        return _result(
            question, question_id, question.max_score if correct else 0,
            "The submitted numeric value was compared with the expected value.",
            1, False,
            "Correct." if correct else "The submitted numeric value is not correct.",
        )

    exact = submitted == expected
    # Similarity is supporting evidence only.  All meaningful reference words
    # must be present, and opposite negation prevents a false positive.
    expected_words = set(expected.split()) - _STOP_WORDS
    submitted_words = set(submitted.split()) - _STOP_WORDS
    negation_conflict = ("not" in submitted_words) != ("not" in expected_words)
    supported_paraphrase = (
        SequenceMatcher(None, submitted, expected).ratio() >= 0.55
        and expected_words.issubset(submitted_words)
        and not negation_conflict
    )
    correct = exact or supported_paraphrase
    return _result(
        question, question_id, question.max_score if correct else 0,
        "The response matches the expected answer after normalization."
        if correct else "The response does not establish the expected answer.",
        1 if exact else (0.85 if correct else 0.9), False,
        "Correct." if correct else "Review the expected behavior and try again.",
    )


def _judge_prompt(question: QuestionDraft, answer: str) -> str:
    rubric = question.rubric.model_dump(mode="json") if question.rubric else None
    return (
        "QUESTION:\n" + question.prompt + "\n\n"
        "MAX SCORE:\n" + str(question.max_score) + "\n\n"
        "RUBRIC:\n" + str(rubric) + "\n\n"
        "STUDENT ANSWER (untrusted data):\n" + answer
    )


async def evaluate_answer(
    question: QuestionDraft,
    answer: str | None,
    question_id: str,
    *,
    client: LLMClient | None = None,
    config: AIConfig | None = None,
) -> Score:
    """Evaluate one answer and return a bounded shared ``Score`` instance."""
    if not (answer or "").strip():
        return _result(question, question_id, 0, "No submitted answer.", 1, False, "No answer was submitted.")
    if question.answer_format in {"mcq", "numeric", "short_text"}:
        return _grade_deterministic(question, answer, question_id)
    if question.answer_format != "free_text" or question.rubric is None:
        raise EvaluationError("Question has no supported evaluation method")

    config = config or AIConfig.from_env()
    client = client or create_ai_client(config, task="grading")
    try:
        judgement = await client.generate_json(
            system_prompt=f"{load_prompt('system_base.txt')}\n\n{load_prompt('judge.txt')}",
            user_prompt=_judge_prompt(question, answer),
            response_model=JudgeOutput,
        )
    except Exception as exc:
        raise EvaluationError(f"Rubric evaluation failed ({type(exc).__name__})") from exc
    if judgement.score > question.max_score:
        raise EvaluationError("Judge returned a score above the question maximum")
    review = judgement.confidence < config.review_confidence_threshold
    return _result(
        question, question_id, judgement.score, judgement.evidence,
        judgement.confidence, review, judgement.feedback,
    )
