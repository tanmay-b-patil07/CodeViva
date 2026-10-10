from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.auth.schemas import TeacherRegisterRequest
from app.auth.service import register_teacher
from app.core.authorization import get_owned_assignment_or_404
from app.core.config import settings
from app.core.errors import AppError
from app.main import app
from app.routers import teacher_assignments
from app.routers.student_exams import (
    _student_question_hint,
)
from app.routers.student_exams import (
    get_assignment as get_student_assignment,
)
from app.routers.student_exams import (
    list_assignments as list_student_assignments,
)
from app.routers.teacher_assignments import (
    _assignment_students,
    release_assignment_questions,
    set_question_release,
)
from app.schemas.assignments import (
    AssignmentStudentResponse,
    StudentQuestionResponse,
    TeacherQuestionRelease,
)
from app.services.analysis_gateway import extract_facts as gateway_extract_facts
from app.services.assignment_workflow import (
    compose_assignment_description,
    get_student_assignment_context,
    split_assignment_description,
)
from app.services.submissions import LANGUAGE_EXTENSIONS, language_for_filename
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql


class FakeResult:
    def __init__(self, rows=(), first_row=None, one_row=None):
        self.rows = rows
        self.first_row = first_row
        self.one_row = one_row

    def first(self):
        return self.first_row

    def all(self):
        return self.rows

    def one(self):
        return self.one_row


class FakeSession:
    def __init__(
        self,
        *,
        scalar_values=(),
        execute_results=(),
        scalars_results=(),
        scalar_statements=None,
    ):
        self.scalar_values = list(scalar_values)
        self.execute_results = list(execute_results)
        self.scalars_results = list(scalars_results)
        self.scalar_statements = scalar_statements if scalar_statements is not None else []
        self.executed_statements = []
        self.committed = False

    def scalar(self, statement):
        self.scalar_statements.append(statement)
        return self.scalar_values.pop(0)

    def execute(self, statement):
        self.executed_statements.append(statement)
        return self.execute_results.pop(0)

    def scalars(self, statement):
        self.executed_statements.append(statement)
        rows = self.scalars_results.pop(0) if self.scalars_results else []
        return FakeResult(rows=rows)

    def commit(self):
        self.committed = True

    def refresh(self, _instance):
        return None

    def add(self, _instance):
        return None


def test_student_assignment_context_hides_nonmember_assignments():
    db = FakeSession(execute_results=[FakeResult(first_row=None)])

    with pytest.raises(HTTPException) as exc:
        get_student_assignment_context(db, uuid4(), uuid4())

    assert exc.value.status_code == 404
    statement = db.executed_statements[0].compile(dialect=postgresql.dialect())
    assert "group_members" in str(statement)
    assert any("student_id" in key for key in statement.params)


def test_teacher_assignment_owner_check_hides_another_teachers_assignment():
    with pytest.raises(HTTPException) as exc:
        get_owned_assignment_or_404(FakeSession(scalar_values=[None]), uuid4(), uuid4())
    assert exc.value.status_code == 404


def test_teacher_registration_requires_configured_server_invite(monkeypatch):
    monkeypatch.setattr(settings, "teacher_invite_code", "")
    request = TeacherRegisterRequest(
        email="teacher@atria.edu.in",
        password="long-password",
        full_name="Atria Teacher",
        invite_code="guessable-default",
    )

    with pytest.raises(AppError) as exc:
        register_teacher(FakeSession(), request)

    assert exc.value.status_code == 503


def test_atria_email_alone_does_not_grant_teacher_registration(monkeypatch):
    monkeypatch.setattr(settings, "teacher_invite_code", "server-only-secret")
    request = TeacherRegisterRequest(
        email="teacher@atria.edu.in",
        password="long-password",
        full_name="Atria Teacher",
        invite_code="wrong",
    )

    with pytest.raises(AppError) as exc:
        register_teacher(FakeSession(), request)

    assert exc.value.status_code == 403


def test_teacher_registration_accepts_invite_code_with_surrounding_whitespace(monkeypatch):
    monkeypatch.setattr(settings, "teacher_invite_code", "server-only-secret")
    request = TeacherRegisterRequest(
        email="teacher@atria.edu.in",
        password="secure-password",
        full_name="Atria Teacher",
        invite_code="  server-only-secret  ",
    )
    db = FakeSession(scalar_values=[None])

    user = register_teacher(db, request)

    assert user.role == "teacher"
    assert db.committed


def test_unreleased_questions_are_not_returned_or_serialized_with_private_fields():
    now = datetime.now(UTC)
    student_id = uuid4()
    assignment = SimpleNamespace(
        id=uuid4(),
        title="Assignment",
        description="Read the code",
        language="python",
        created_at=now,
        due_at=now + timedelta(days=1),
        teacher_id=uuid4(),
    )
    exam = SimpleNamespace(id=uuid4())
    slot = SimpleNamespace(
        id=uuid4(),
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(days=1),
    )
    group = SimpleNamespace(id=uuid4(), name="Batch A")
    db = FakeSession(
        scalar_values=["Teacher", None, None, None, None],
        execute_results=[FakeResult(first_row=(assignment, exam, slot, group))],
    )

    response = get_student_assignment(assignment.id, SimpleNamespace(id=student_id), db)

    assert response.questions == []
    assert not {"answer_key", "rubric", "hidden_tests"} & StudentQuestionResponse.model_fields.keys()
    question_query = db.executed_statements[-1].compile(dialect=postgresql.dialect())
    assert "approved" in question_query.params.values()
    assert student_id in question_query.params.values()


def test_released_question_is_returned_without_answer_key_or_rubric():
    now = datetime.now(UTC)
    student_id = uuid4()
    assignment = SimpleNamespace(
        id=uuid4(),
        title="Assignment",
        description=None,
        language="python",
        created_at=now,
        due_at=None,
        teacher_id=uuid4(),
    )
    question = SimpleNamespace(
        id=uuid4(),
        order_idx=1,
        type="short_answer",
        prompt="Explain the loop.",
        line_refs=[{"line": 2}, {"line": 4}],
        answer_format="text",
        options=None,
    )
    slot = SimpleNamespace(
        id=uuid4(),
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(days=1),
    )
    db = FakeSession(
        scalar_values=["Teacher", None, None, None, None],
        execute_results=[
            FakeResult(
                first_row=(
                    assignment,
                    SimpleNamespace(id=uuid4()),
                    slot,
                    SimpleNamespace(id=uuid4(), name="Batch"),
                )
            )
        ],
        scalars_results=[[question]],
    )

    response = get_student_assignment(
        assignment.id,
        SimpleNamespace(id=student_id),
        db,
    )

    assert [item.id for item in response.questions] == [question.id]
    assert response.questions[0].hint == (
        "Start by reviewing line(s) 2, 4. Trace how the values there lead to "
        "the behavior asked about."
    )
    assert not {"answer_key", "rubric"} & StudentQuestionResponse.model_fields.keys()
    question_query = db.executed_statements[-1].compile(dialect=postgresql.dialect())
    assert "approved" in question_query.params.values()
    assert student_id in question_query.params.values()


def test_student_question_hint_uses_safe_line_references_only():
    hint = _student_question_hint(
        [{"line": 7}, {"line": 3}, {"line": 7}, {"line": -1}, {}]
    )

    assert "line(s) 3, 7" in hint
    assert "answer_key" not in hint
    assert "rubric" not in hint


def test_student_question_without_line_references_gets_general_reasoning_hint():
    hint = _student_question_hint([])

    assert "relevant function" in hint
    assert "inputs" in hint


def test_student_assignment_list_includes_only_their_released_question_prompts():
    now = datetime.now(UTC)
    student_id = uuid4()
    assignment = SimpleNamespace(
        id=uuid4(),
        title="Assignment",
        description=None,
        language="python",
        created_at=now,
        due_at=None,
        teacher_id=uuid4(),
    )
    slot = SimpleNamespace(
        id=uuid4(),
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(days=1),
    )
    group = SimpleNamespace(id=uuid4(), name="Batch")
    question = SimpleNamespace(
        id=uuid4(),
        order_idx=1,
        type="short_answer",
        prompt="Explain the loop.",
        line_refs=[{"line": 5}],
        answer_format="text",
        options=None,
    )
    db = FakeSession(
        scalar_values=[None, None, "Teacher"],
        execute_results=[
            FakeResult(
                rows=[(assignment, slot, group, "Teacher")]
            )
        ],
        scalars_results=[[question]],
    )

    response = list_student_assignments(
        SimpleNamespace(id=student_id),
        db,
    )

    assert response[0].questions[0].prompt == "Explain the loop."
    assert "line(s) 5" in response[0].questions[0].hint
    question_query = db.executed_statements[-1].compile(
        dialect=postgresql.dialect()
    )
    assert "approved" in question_query.params.values()
    assert student_id in question_query.params.values()


def test_teacher_roster_keeps_assigned_students_who_have_not_submitted():
    student_id = uuid4()
    assignment = SimpleNamespace(id=uuid4(), due_at=None)
    slot = SimpleNamespace(id=uuid4())
    group = SimpleNamespace(id=uuid4())
    rows = [(student_id, "Ada Student", "ada@example.com")]
    db = FakeSession(
        scalar_values=[None, None, 0, 0],
        execute_results=[
            FakeResult(rows=rows),
            FakeResult(one_row=(None, None, 0)),
        ],
    )

    students = _assignment_students(db, assignment, slot, group)

    assert len(students) == 1
    assert students[0].student_id == student_id
    assert students[0].submission_id is None
    assert students[0].status == "Available"
    assert students[0].score is None
    assert students[0].max_score is None


def test_teacher_explicitly_releases_questions_only_after_owner_check():
    teacher_id = uuid4()
    assignment = SimpleNamespace(id=uuid4(), teacher_id=teacher_id)
    question = SimpleNamespace(
        id=uuid4(),
        student_id=uuid4(),
        prompt="What does this function return?",
        order_idx=1,
        max_score=1,
        status="draft",
    )
    db = FakeSession(scalar_values=[assignment, question])

    result = set_question_release(
        assignment.id,
        question.id,
        TeacherQuestionRelease(released=True),
        SimpleNamespace(id=teacher_id),
        db,
    )

    assert result.status == "approved"
    assert question.status == "approved"
    assert db.committed


def test_teacher_can_release_all_draft_questions_for_assignment():
    teacher_id = uuid4()
    assignment = SimpleNamespace(id=uuid4(), teacher_id=teacher_id)
    draft_questions = [
        SimpleNamespace(status="draft"),
        SimpleNamespace(status="draft"),
    ]
    db = FakeSession(
        scalar_values=[assignment],
        execute_results=[
            FakeResult(
                first_row=(
                    SimpleNamespace(id=uuid4()),
                    SimpleNamespace(id=uuid4()),
                    SimpleNamespace(id=uuid4()),
                )
            )
        ],
        scalars_results=[draft_questions],
    )

    result = release_assignment_questions(
        assignment.id,
        SimpleNamespace(id=teacher_id),
        db,
    )

    assert result.released_questions == 2
    assert all(question.status == "approved" for question in draft_questions)
    assert db.committed


def test_bulk_question_release_rejects_non_owner():
    db = FakeSession(scalar_values=[None])

    with pytest.raises(HTTPException) as exc:
        release_assignment_questions(
            uuid4(),
            SimpleNamespace(id=uuid4()),
            db,
        )

    assert exc.value.status_code == 404
    assert not db.committed


def test_teacher_marks_card_includes_saved_attempt_summary(monkeypatch):
    assignment_id = uuid4()
    student_id = uuid4()
    assignment = SimpleNamespace(id=assignment_id)
    slot = SimpleNamespace(id=uuid4())
    group = SimpleNamespace(id=uuid4())
    student = SimpleNamespace(id=student_id)
    computed_at = datetime.now(UTC)
    attempt_result = SimpleNamespace(
        comprehension_index=80,
        sub_scores={"question-1": {"score": "8", "max_score": "10"}},
        flag_oral_followup=False,
        needs_review_count=1,
        computed_at=computed_at,
    )
    summary = AssignmentStudentResponse(
        student_id=student_id,
        full_name="Ada Student",
        email="ada@example.com",
        submission_id=None,
        submission_filename=None,
        submitted_at=None,
        status="Completed",
        released_questions=1,
        answered_questions=1,
        score=8,
        max_score=10,
        graded_answers=1,
        submitted_attempt=True,
    )
    db = FakeSession(
        scalar_values=[student, None, attempt_result],
        execute_results=[FakeResult(rows=[])],
    )
    monkeypatch.setattr(
        teacher_assignments,
        "get_owned_assignment_or_404",
        lambda *_args: assignment,
    )
    monkeypatch.setattr(
        teacher_assignments,
        "_assignment_slot",
        lambda *_args: (SimpleNamespace(id=uuid4()), slot, group),
    )
    monkeypatch.setattr(
        teacher_assignments,
        "_assignment_students",
        lambda *_args: [summary],
    )

    result = teacher_assignments.get_student_assignment_detail(
        assignment_id,
        student_id,
        SimpleNamespace(id=uuid4()),
        db,
    )

    assert result.student.score == 8
    assert result.student.max_score == 10
    assert result.attempt_result is not None
    assert result.attempt_result.comprehension_index == 80
    assert result.attempt_result.needs_review_count == 1
    assert result.attempt_result.computed_at == computed_at
    assert len(db.scalar_statements) == 3


def test_assignment_instructions_round_trip_without_schema_migration():
    stored = compose_assignment_description("Description", "Instructions")
    assert split_assignment_description(stored) == ("Description", "Instructions")
    assert split_assignment_description("Existing description") == (
        "Existing description",
        None,
    )


@pytest.mark.parametrize(
    ("language", "extension"),
    [
        ("python", ".py"),
        ("c", ".c"),
        ("cpp", ".cc"),
        ("java", ".java"),
        ("javascript", ".mjs"),
        ("go", ".go"),
    ],
)
def test_supported_adapter_upload_extension(language, extension):
    assert extension in LANGUAGE_EXTENSIONS[language]
    assert language_for_filename("solution" + extension) == language


def test_unsupported_upload_extension_is_rejected():
    with pytest.raises(AppError, match="Unsupported source file type"):
        language_for_filename("solution.rs")


def test_language_specific_upload_uses_existing_analysis_adapter(monkeypatch):
    import sys

    from backend import analysis

    monkeypatch.setitem(sys.modules, "analysis", analysis)
    facts = gateway_extract_facts(
        "int add(int a, int b) { return a + b; }",
        "c",
    )
    assert facts["language"] == "c"


def test_assignment_routes_are_registered_and_student_schema_is_private():
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/teacher/assignments/{assignment_id}/questions/{question_id}/release" in paths
    assert "/api/student/assignments/{assignment_id}/attempts/{attempt_id}/answers" in paths
    assert "/api/student/submissions/code" in paths
    question_schema = schema["components"]["schemas"]["StudentQuestionResponse"]
    assert not {"answer_key", "rubric"} & question_schema["properties"].keys()
    answer_schema = schema["components"]["schemas"]["StudentAnswerResponse"]
    assert {"score", "max_score", "feedback"} & answer_schema["properties"].keys()
