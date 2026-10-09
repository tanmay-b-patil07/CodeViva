"""Validated, provider-routed grading boundary.

This module deliberately accepts only server-built ``GradingAttemptInput`` and
returns only the application's normalized ``GradingResult``.  Provider output
cannot choose an attempt, question, or score maximum.
"""

from decimal import Decimal

try:  # Support both the deployed ``app`` package and repository-root tests.
    from ai.client import LLMClient
    from ai.config import AIConfig
    from ai.evaluator import EvaluationError, evaluate_answer
    from ai.schemas import QuestionDraft

    from app.schemas.grading import (
        GradingAttemptInput,
        GradingResult,
        QuestionGrade,
    )
except ModuleNotFoundError:  # pragma: no cover - import layout compatibility.
    from backend.ai.client import LLMClient
    from backend.ai.config import AIConfig
    from backend.ai.evaluator import EvaluationError, evaluate_answer
    from backend.ai.schemas import QuestionDraft
    from backend.app.schemas.grading import (
        GradingAttemptInput,
        GradingResult,
        QuestionGrade,
    )


class GradingGatewayError(RuntimeError):
    """A safe failure from the external grading boundary."""


def _evaluator_question(question) -> QuestionDraft:
    """Map the private application record to the Phase 4 evaluator contract."""
    try:
        return QuestionDraft(
            type=question.type,
            prompt=question.prompt,
            line_refs=[1],  # Line references are not part of grading input.
            answer_format=question.answer_format,
            max_score=float(question.max_score),
            answer_key=question.answer_key,
            rubric=question.rubric,
        )
    except Exception as exc:
        raise GradingGatewayError(
            "Stored question cannot be evaluated by the Phase 4 contract"
        ) from exc


async def grade_attempt(
    payload: GradingAttemptInput,
    *,
    client: LLMClient | None = None,
    config: AIConfig | None = None,
) -> GradingResult:
    """Grade every server-authorized question and calculate the total locally.

    ``payload`` is the stable public contract used by ``grading_service``.
    Dependency injection is keyword-only so offline tests can supply fakes.
    Missing answers are deterministically scored zero without a provider call.
    """
    if not payload.questions:
        raise GradingGatewayError("Cannot grade an attempt with no questions")

    config = config or AIConfig.from_env()
    grades: list[QuestionGrade] = []
    total = Decimal(0)

    for index, question in enumerate(payload.questions):
        try:
            evaluated = await evaluate_answer(
                _evaluator_question(question),
                question.answer.answer_text if question.answer else None,
                str(question.id),
                client=client,
                config=config,
            )
        except EvaluationError as exc:
            raise GradingGatewayError(str(exc)) from exc
        grade = QuestionGrade(
            question_id=question.id,
            awarded_score=Decimal(str(evaluated.score)),
            max_score=question.max_score,
            feedback=evaluated.feedback,
            evidence=evaluated.evidence,
            confidence=Decimal(str(evaluated.confidence)),
            needs_review=evaluated.needs_review,
        )
        grades.append(grade)
        total += grade.awarded_score

    return GradingResult(
        attempt_id=payload.attempt_id,
        total_score=total,
        max_score=sum(
            (question.max_score for question in payload.questions), Decimal(0)
        ),
        question_grades=grades,
    )
