"""Offline integration tests across the actual Phase 4/5 application bridge."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.exam import exam_cache
from ai.schemas import JudgeOutput, QuestionDraft
from analysis.analyzer import extract_facts
from app.schemas.exam_runtime import QuestionPublic
from app.schemas.grading import (
    GradingAnswerInput,
    GradingAttemptInput,
    GradingQuestionInput,
)
from app.services import exam_generation_gateway
from app.services.grading_gateway import grade_attempt
from app.services.grading_service import _comprehension_for_result


class FakeJudge:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def generate_json(self, **_kwargs):
        self.calls += 1
        return self.result


def test_analysis_facts_flow_through_member1_gateway_to_member3(monkeypatch):
    """Use Member 2 facts, Member 1's gateway, and Member 3's batch contract."""
    code = "def answer():\n    return 42\n"
    facts = extract_facts(code).model_dump(mode="json")
    generated = QuestionDraft(
        type="complexity",
        prompt="What is the complexity of answer?",
        line_refs=[1],
        answer_format="short_text",
        answer_key="O(1)",
    )
    import ai as backend_ai
    import ai.exam as backend_exam

    monkeypatch.setitem(sys.modules, "ai", backend_ai)
    monkeypatch.setitem(sys.modules, "ai.exam", backend_exam)
    monkeypatch.setattr(
        backend_exam, "_deterministic_questions", lambda *_: [generated]
    )
    exam_cache.clear()

    result = asyncio.run(
        exam_generation_gateway.generate_exam_questions(code, facts, 1, set())
    )

    assert facts["language"] == "python"
    assert result[0].prompt == generated.prompt
    assert result[0].question_hash


def test_public_exam_schema_removes_private_question_fields():
    private_question = SimpleNamespace(
        id=uuid4(),
        order_idx=1,
        type="complexity",
        prompt="Question?",
        line_refs=[1],
        answer_format="short_text",
        options=None,
        answer_key="private",
        rubric={"private": "rubric"},
        explanation="private",
        question_hash="private-hash",
        metadata={"fallback": True},
    )
    public = QuestionPublic.model_validate(private_question).model_dump()
    assert public == {
        "id": private_question.id,
        "order_idx": 1,
        "type": "complexity",
        "prompt": "Question?",
        "line_refs": [1],
        "answer_format": "short_text",
        "options": None,
    }


def test_real_gateway_uses_evaluator_then_maps_result_to_comprehension_index():
    question_id = uuid4()
    payload = GradingAttemptInput(
        attempt_id=uuid4(),
        student_id=uuid4(),
        slot_id=uuid4(),
        questions=[
            GradingQuestionInput(
                id=question_id,
                prompt="What is the complexity of the loop?",
                type="complexity",
                answer_format="free_text",
                answer_key=None,
                rubric={
                    "expected_points": ["States linear complexity"],
                    "common_misconceptions": [],
                    "scoring_guide": "Award a correct complexity explanation.",
                },
                max_score=Decimal(10),
                answer=GradingAnswerInput(
                    question_id=question_id, answer_text="It visits each item once."
                ),
            )
        ],
    )
    judge = FakeJudge(
        JudgeOutput(
            score=8, evidence="Explains one pass.", confidence=0.8, feedback="Good."
        )
    )

    result = asyncio.run(grade_attempt(payload, client=judge))
    index = _comprehension_for_result(payload, result)

    assert judge.calls == 1
    assert result.question_grades[0].awarded_score == Decimal(8)
    assert result.question_grades[0].needs_review is False
    assert index is not None
    assert index.comprehension_index == 80
    assert index.sub_scores == {"complexity": 80}
    assert index.needs_review_count == 0


def test_unmapped_phase3_what_if_question_does_not_claim_a_complete_index():
    question_id = uuid4()
    payload = GradingAttemptInput(
        attempt_id=uuid4(),
        student_id=uuid4(),
        slot_id=uuid4(),
        questions=[
            GradingQuestionInput(
                id=question_id,
                prompt="What if the condition changed?",
                type="what_if",
                answer_format="free_text",
                answer_key=None,
                rubric={
                    "expected_points": ["Explains effect"],
                    "common_misconceptions": [],
                    "scoring_guide": "Relevant effect.",
                },
                max_score=Decimal(10),
                answer=GradingAnswerInput(
                    question_id=question_id, answer_text="It changes the branch."
                ),
            )
        ],
    )
    result = asyncio.run(
        grade_attempt(
            payload,
            client=FakeJudge(
                JudgeOutput(
                    score=6, evidence="Relevant.", confidence=0.9, feedback="OK."
                )
            ),
        )
    )
    assert _comprehension_for_result(payload, result) is None
