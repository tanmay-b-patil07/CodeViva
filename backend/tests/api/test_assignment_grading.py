from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.routers import student_exams
from app.services.ai_assignment_service import (
    AnswerEvaluation,
    AttemptEvaluation,
)


class FakeResult:
    def __init__(self, first_row):
        self.first_row = first_row

    def first(self):
        return self.first_row

    def all(self):
        return [self.first_row]


class FakeSession:
    def __init__(self, *, scalar_values, execute_results):
        self.scalar_values = list(scalar_values)
        self.execute_results = list(execute_results)
        self.added = []
        self.committed = False

    def execute(self, _statement):
        return self.execute_results.pop(0)

    def scalar(self, _statement):
        return self.scalar_values.pop(0)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, _value):
        return None


def test_submitting_answers_persists_ai_scores_and_marks_attempt_complete(monkeypatch):
    assignment_id = uuid4()
    student_id = uuid4()
    question_id = uuid4()
    attempt_id = uuid4()
    slot_id = uuid4()
    source = SimpleNamespace(
        id=uuid4(),
        code="def add(a, b):\n    return a + b",
    )
    assignment = SimpleNamespace(id=assignment_id, language="python")
    exam = SimpleNamespace(id=uuid4())
    slot = SimpleNamespace(id=slot_id)
    group = SimpleNamespace(id=uuid4())
    attempt = SimpleNamespace(
        id=attempt_id,
        slot_id=slot_id,
        student_id=student_id,
        submitted_at=None,
        started_at=datetime.now(UTC) - timedelta(minutes=1),
        deadline_at=datetime.now(UTC) + timedelta(minutes=10),
        auto_submitted=False,
    )
    question = SimpleNamespace(
        id=question_id,
        prompt="Explain what the function returns.",
        order_idx=1,
        answer_key={"expected_answer": "The sum of the two arguments."},
        rubric={"criteria": "Explain the returned addition."},
        max_score=Decimal(4),
    )
    answer = SimpleNamespace(
        id=uuid4(),
        attempt_id=attempt_id,
        question_id=question_id,
        answer_text="It returns a plus b.",
    )
    db = FakeSession(
        scalar_values=[attempt, source],
        execute_results=[
            FakeResult((assignment, exam, slot, group)),
            FakeResult((question, answer)),
        ],
    )
    monkeypatch.setattr(
        student_exams,
        "evaluate_attempt",
        lambda **_kwargs: AttemptEvaluation(
            evaluations=[
                AnswerEvaluation(
                    question_id=str(question_id),
                    score=Decimal("3.5"),
                    confidence=Decimal("0.9"),
                    evidence="The answer identifies addition as the operation.",
                    feedback="State explicitly that both argument values are added.",
                )
            ]
        ),
    )

    result = student_exams.submit_attempt(
        assignment_id,
        attempt_id,
        SimpleNamespace(id=student_id),
        db,
    )

    saved_score = next(item for item in db.added if item.__class__.__name__ == "Score")
    assert saved_score.score == Decimal("3.5")
    assert saved_score.max_score == Decimal(4)
    assert saved_score.evidence.startswith("The answer identifies")
    assert saved_score.feedback.startswith("State explicitly")
    assert saved_score.needs_review is False
    result_sheet = next(
        item for item in db.added if isinstance(item, student_exams.AttemptResult)
    )
    assert result_sheet.comprehension_index == Decimal("87.50")
    assert result_sheet.sub_scores == {
        str(question_id): {"score": "3.5", "max_score": "4"}
    }
    assert result_sheet.needs_review_count == 0
    assert attempt.submitted_at is not None
    assert result.submitted_at == attempt.submitted_at
    assert db.committed


def test_student_attempt_detail_returns_saved_understanding_score():
    assignment_id = uuid4()
    student_id = uuid4()
    slot_id = uuid4()
    attempt_id = uuid4()
    now = datetime.now(UTC)
    attempt = SimpleNamespace(
        id=attempt_id,
        slot_id=slot_id,
        student_id=student_id,
        submitted_at=now,
        started_at=now - timedelta(minutes=1),
        deadline_at=now + timedelta(minutes=10),
        auto_submitted=False,
    )
    attempt_result = SimpleNamespace(
        comprehension_index=Decimal("87.50"),
        needs_review_count=1,
        computed_at=now,
        sub_scores={"private_detail": "not returned"},
    )
    answer = SimpleNamespace(
        id=uuid4(),
        question_id=uuid4(),
        answer_text="It returns the sum.",
        saved_at=now,
    )
    db = FakeSession(
        scalar_values=[attempt, attempt_result],
        execute_results=[
            FakeResult(
                (
                    SimpleNamespace(id=assignment_id),
                    SimpleNamespace(id=uuid4()),
                    SimpleNamespace(id=slot_id),
                    SimpleNamespace(id=uuid4()),
                )
            ),
            FakeResult((answer, None)),
        ],
    )

    result = student_exams.get_current_attempt(
        assignment_id,
        SimpleNamespace(id=student_id),
        db,
    )

    assert result is not None
    assert result.attempt_result is not None
    assert result.attempt_result.comprehension_index == Decimal("87.50")
    assert result.attempt_result.needs_review_count == 1
    assert not hasattr(result.attempt_result, "sub_scores")
