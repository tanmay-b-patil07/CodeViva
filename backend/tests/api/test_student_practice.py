from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.routers import student_practice
from app.services.ai_assignment_service import AnswerEvaluation, AttemptEvaluation


class FakeSession:
    def __init__(self, scalar_values, submission):
        self.scalar_values = list(scalar_values)
        self.submission = submission
        self.added = []
        self.committed = False

    def scalar(self, _statement):
        return self.scalar_values.pop(0)

    def get(self, model, _identity):
        if model.__name__ == "Submission":
            return self.submission
        return None

    def add(self, value):
        if getattr(value, "id", None) is None and hasattr(value, "id"):
            value.id = uuid4()
        if getattr(value, "created_at", None) is None and hasattr(value, "created_at"):
            value.created_at = datetime.now(UTC)
        self.added.append(value)

    def commit(self):
        self.committed = True
        for value in self.added:
            if getattr(value, "id", None) is None and hasattr(value, "id"):
                value.id = uuid4()
            if getattr(value, "created_at", None) is None and hasattr(value, "created_at"):
                value.created_at = datetime.now(UTC)

    def refresh(self, _value):
        return None

    def flush(self):
        self.commit()


def test_practice_answer_is_saved_and_graded_by_ai(monkeypatch):
    session_id = uuid4()
    student_id = uuid4()
    question_id = uuid4()
    session = SimpleNamespace(
        id=session_id,
        student_id=student_id,
        submission_id=uuid4(),
        status="ready",
    )
    question = SimpleNamespace(
        id=question_id,
        session_id=session_id,
        prompt="What does this function return?",
        answer_key={
            "expected_answer": "The sum.",
            "rubric": "Explain the addition.",
            "max_score": "10",
        },
        explanation="Explain the addition.",
    )
    submission = SimpleNamespace(
        id=session.submission_id,
        code="def add(a, b): return a + b",
        code_facts={"language": "python"},
    )
    db = FakeSession([session, question, None], submission)
    called = {}

    def grade(**kwargs):
        called.update(kwargs)
        return AttemptEvaluation(
            evaluations=[
                AnswerEvaluation(
                    question_id=str(question_id),
                    score=Decimal(8),
                    confidence=Decimal("0.9"),
                    evidence="The answer identifies the sum.",
                    feedback="Good explanation.",
                )
            ]
        )

    monkeypatch.setattr(student_practice, "evaluate_attempt", grade)
    result = student_practice.save_and_grade_practice_answer(
        session_id,
        question_id,
        SimpleNamespace(answer_text="It adds both values."),
        SimpleNamespace(id=student_id),
        db,
    )

    saved_answer = db.added[0]
    assert saved_answer.answer_text == "It adds both values."
    assert saved_answer.score == Decimal(8)
    assert saved_answer.is_correct is False
    assert "Good explanation." in saved_answer.feedback
    assert result.score == Decimal(8)
    assert result.grading_status == "complete"
    assert called["source_code"] == submission.code
    assert called["answers"][0]["expected_answer"] == "The sum."
    assert db.committed


def test_practice_questions_never_serialize_private_answer_key():
    question = SimpleNamespace(
        id=uuid4(),
        order_idx=1,
        prompt="Explain the loop.",
        line_refs=[{"line": 1}],
        answer_key={"expected_answer": "Private answer", "max_score": "10"},
    )

    response = student_practice._question_response(question, None)

    assert response.prompt == "Explain the loop."
    assert response.max_score == Decimal(10)
    assert "answer_key" not in response.model_dump()
    assert "expected_answer" not in response.model_dump()


def test_open_practice_submission_persists_ai_questions(monkeypatch):
    from app.routers import submissions
    from app.schemas.assignments import CodeSubmissionCreate
    from app.services.ai_assignment_service import (
        CodeReview,
        GeneratedAssignmentAssessment,
        GeneratedQuestion,
    )

    db = FakeSession([None], submission=None)
    monkeypatch.setattr(
        submissions,
        "extract_facts",
        lambda *_args: {"language": "python", "line_count": 1},
    )
    monkeypatch.setattr(
        submissions,
        "analyze_assignment_code",
        lambda **_kwargs: GeneratedAssignmentAssessment(
            code_review=CodeReview(
                summary="A small addition function.",
                code_suggestions=["Add input validation."],
                understanding_suggestions=["Explain the return value."],
            ),
            questions=[
                GeneratedQuestion(
                    prompt="What does this function return?",
                    expected_answer="The sum of the arguments.",
                    rubric="Mention that both arguments are added.",
                )
            ],
        ),
    )

    result = submissions.submit_code(
        CodeSubmissionCreate(
            code="def add(a, b): return a + b",
            language="python",
        ),
        SimpleNamespace(id=uuid4()),
        db,
    )

    saved_session = next(
        item for item in db.added if item.__class__.__name__ == "PracticeSession"
    )
    saved_question = next(
        item for item in db.added if item.__class__.__name__ == "PracticeQuestion"
    )
    assert result.practice_session_id == saved_session.id
    assert saved_session.status == "ready"
    assert saved_question.session_id == saved_session.id
    assert result.practice_questions[0].id == saved_question.id
    assert result.practice_questions[0].prompt == saved_question.prompt
    assert not hasattr(result.practice_questions[0], "answer_key")
