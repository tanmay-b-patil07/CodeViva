"""Cross-cutting authentication, authorization, and error-boundary regressions."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import AUTH_COOKIE_NAME, create_access_token
from app.db.models import Profile, Submission
from app.db.session import get_db
from app.main import app


def _user(email: str) -> Profile:
    db = next(get_db())
    try:
        user = db.scalar(select(Profile).where(Profile.email == email))
        assert user is not None, f"Expected existing test user {email}"
        return user
    finally:
        db.close()


def _client(user: Profile) -> TestClient:
    client = TestClient(app)
    client.cookies.set(
        AUTH_COOKIE_NAME,
        create_access_token(user.id, user.role),
        domain="testserver.local",
        path="/",
    )
    return client


def test_session_authentication_me_logout_and_invalid_tokens():
    student = _user("student1@example.com")
    anonymous = TestClient(app)
    protected = "/api/student/slots"

    assert anonymous.get(protected).status_code == 401
    assert anonymous.get("/api/auth/me").status_code == 401

    invalid = TestClient(app)
    invalid.cookies.set(AUTH_COOKIE_NAME, "not.a.valid.token")
    assert invalid.get(protected).status_code == 401
    assert invalid.get("/api/auth/me").status_code == 401

    expired = TestClient(app)
    expired_token = jwt.encode(
        {
            "sub": str(student.id),
            "role": "student",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    expired.cookies.set(AUTH_COOKIE_NAME, expired_token)
    assert expired.get(protected).status_code == 401

    client = _client(student)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "id": str(student.id),
        "email": student.email,
        "full_name": student.full_name,
        "role": "student",
    }

    logged_out = client.post("/api/auth/logout")
    assert logged_out.status_code == 200
    assert "max-age=0" in logged_out.headers["set-cookie"].lower()
    assert AUTH_COOKIE_NAME not in client.cookies
    assert client.get(protected).status_code == 401


def test_role_guards_cover_student_and_teacher_surfaces():
    student = _client(_user("student1@example.com"))
    teacher = _client(_user("teacher1@example.com"))

    assert student.get("/api/teacher/assignments").status_code == 403
    assert student.get("/api/teacher/exams").status_code == 403
    assert student.get("/api/teacher/groups").status_code == 403
    assert student.get("/api/teacher/results").status_code == 403
    assert teacher.get("/api/student/slots").status_code == 403
    assert teacher.get(f"/api/student/attempts/{uuid4()}/result").status_code == 403


def test_error_boundary_does_not_reveal_guessed_resource_data():
    student = _client(_user("student1@example.com"))

    missing = student.get(f"/api/student/attempts/{uuid4()}/result")
    assert missing.status_code == 404
    assert "answer_key" not in missing.text
    assert "grading_error" not in missing.text

    malformed_uuid = student.get("/api/student/attempts/not-a-uuid/result")
    assert malformed_uuid.status_code == 422
    assert malformed_uuid.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
        }
    }

    unknown_route = student.get("/api/student/not-a-real-endpoint")
    assert unknown_route.status_code == 404
    assert "answer_key" not in unknown_route.text


def test_submission_api_is_authenticated_and_lists_only_the_owner(monkeypatch):
    from app.routers import submissions as submissions_router

    student_a = _user("student1@example.com")
    student_b = _user("student2@example.com")
    teacher = _user("teacher1@example.com")
    clients = {user.id: _client(user) for user in (student_a, student_b, teacher)}
    source = f"print('phase15-{uuid4()}')\n"
    facts = {"language": "python", "functions": [], "imports": []}
    monkeypatch.setattr(submissions_router, "extract_facts", lambda _code: facts)

    db = next(get_db())
    submission_id = None
    try:
        assert TestClient(app).get("/api/student/submissions").status_code == 401
        assert clients[teacher.id].get("/api/student/submissions").status_code == 403

        created = clients[student_a.id].post(
            "/api/student/submissions",
            files={"file": ("answer.py", source.encode(), "text/x-python")},
        )
        assert created.status_code == 201, created.text
        body = created.json()
        submission_id = body["id"]
        assert body["code_hash"].startswith("sha256:")
        assert body["code_facts"] == facts
        assert "code" not in body

        own_list = clients[student_a.id].get("/api/student/submissions")
        other_list = clients[student_b.id].get("/api/student/submissions")
        assert own_list.status_code == other_list.status_code == 200
        assert submission_id in {row["id"] for row in own_list.json()}
        assert submission_id not in {row["id"] for row in other_list.json()}
    finally:
        if submission_id:
            db.query(Submission).filter(Submission.id == submission_id).delete()
            db.commit()
        db.close()


def test_submission_rejects_missing_assignment_before_cache_or_analysis(monkeypatch):
    from app.db.models import Assignment
    from app.routers import submissions as submissions_router

    student = _client(_user("student1@example.com"))
    teacher = _user("teacher1@example.com")
    assignment_db = next(get_db())
    assignment = Assignment(
        teacher_id=teacher.id,
        title=f"Submission authorization {uuid4()}",
        language="python",
    )
    assignment_db.add(assignment)
    assignment_db.commit()
    assignment_db.refresh(assignment)
    cache_calls = []
    analysis_calls = []
    monkeypatch.setattr(
        submissions_router,
        "find_cached_facts",
        lambda *args, **kwargs: cache_calls.append((args, kwargs)),
    )
    def fake_extract_facts(code):
        analysis_calls.append(code)
        return {"synthetic": True}

    monkeypatch.setattr(submissions_router, "extract_facts", fake_extract_facts)
    submission_id = None

    try:
        missing = student.post(
            "/api/student/submissions",
            files={"file": ("missing.py", b"print('safe')\n", "text/x-python")},
            data={"assignment_id": str(uuid4())},
        )
        assert missing.status_code == 404
        assert missing.json() == {
            "error": {"code": "NOT_FOUND", "message": "Assignment not found."}
        }
        assert cache_calls == []
        assert analysis_calls == []

        malformed = student.post(
            "/api/student/submissions",
            files={"file": ("malformed.py", b"print('safe')\n", "text/x-python")},
            data={"assignment_id": "not-a-uuid"},
        )
        assert malformed.status_code == 422
        assert malformed.json() == {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
            }
        }
        assert cache_calls == []
        assert analysis_calls == []

        valid = student.post(
            "/api/student/submissions",
            files={"file": ("valid.py", b"print('safe')\n", "text/x-python")},
            data={"assignment_id": str(assignment.id)},
        )
        assert valid.status_code == 201, valid.text
        submission_id = valid.json()["id"]
        assert valid.json()["assignment_id"] == str(assignment.id)
        assert valid.json()["code_facts"] == {"synthetic": True}
        assert cache_calls and len(analysis_calls) == 1
    finally:
        if submission_id:
            from app.db.models import Submission

            assignment_db.query(Submission).filter(
                Submission.id == submission_id
            ).delete()
        assignment_db.delete(assignment)
        assignment_db.commit()
        assignment_db.close()
