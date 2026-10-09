
"""Route-level tests for CodeViva student practice and SSE."""

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import PracticeQuestion, PracticeSession, Submission
from app.routers import student_practice as routes
from app.schemas.practice import PracticeStartRequest


class FakeResult:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def all(self):
        return self.rows


class FakeDB:
    """Small database double for exercising routes without PostgreSQL."""

    def __init__(self, submission=None):
        self.submission = submission
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, item):
        if getattr(item, "id", None) is None:
            item.id = uuid4()

    def get(self, model, record_id):
        if model is Submission and self.submission is not None:
            if self.submission.id == record_id:
                return self.submission
        return None

    def scalars(self, statement):
        return FakeResult([])


def make_submission(student_id):
    return Submission(
        id=uuid4(),
        student_id=student_id,
        filename="main.py",
        code="def f():\n    return 2",
        code_hash="test-code-hash",
        code_facts={},
    )


def make_session(student_id, submission_id, status="generating"):
    return PracticeSession(
        id=uuid4(),
        student_id=student_id,
        submission_id=submission_id,
        status=status,
    )


def collect_response(response):
    async def run():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(
                chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            )
        return "".join(chunks)

    return asyncio.run(run())


def test_practice_start_and_stream_routes_are_registered():
    registered_routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in routes.router.routes
    }

    assert ("/student/practice", ("POST",)) in registered_routes
    assert (
        "/student/practice/{session_id}/stream",
        ("GET",),
    ) in registered_routes


def test_sse_event_has_correct_format():
    event = routes._sse(
        "question",
        {"id": "q1", "prompt": "Explain this line."},
    )

    assert event.startswith("event: question\n")
    assert event.endswith("\n\n")

    data_line = next(
        line.removeprefix("data: ")
        for line in event.splitlines()
        if line.startswith("data: ")
    )
    data = json.loads(data_line)

    assert data["id"] == "q1"
    assert data["prompt"] == "Explain this line."


def test_answer_key_adapter_preserves_scalar_and_object_values():
    scalar = routes._store_answer_key("42")
    assert scalar == {"__codeviva_scalar__": "42"}
    assert routes._read_answer_key(scalar) == "42"

    answer_object = {"expected": ["a", "b"]}
    assert routes._store_answer_key(answer_object) == answer_object
    assert routes._read_answer_key(answer_object) == answer_object


def test_null_answer_key_remains_null():
    assert routes._store_answer_key(None) is None
    assert routes._read_answer_key(None) is None


def test_start_practice_creates_generating_session(monkeypatch):
    student_id = uuid4()
    submission = make_submission(student_id)
    db = FakeDB(submission=submission)
    user = SimpleNamespace(id=student_id)

    monkeypatch.setattr(
        routes,
        "get_student_submission_or_404",
        lambda database, submission_id, requested_student_id: submission,
    )

    response = routes.start_practice(
        PracticeStartRequest(submission_id=submission.id),
        user,
        db,
    )

    assert response.status == "generating"
    assert response.session_id is not None
    assert db.commits == 1
    assert any(isinstance(item, PracticeSession) for item in db.added)


def test_stream_emits_question_then_done_and_persists(monkeypatch):
    student_id = uuid4()
    submission = make_submission(student_id)
    session = make_session(student_id, submission.id)
    db = FakeDB(submission=submission)
    user = SimpleNamespace(id=student_id)

    monkeypatch.setattr(
        routes,
        "get_student_practice_session_or_404",
        lambda database, session_id, requested_student_id: session,
    )
    monkeypatch.setattr(
        routes,
        "_load_saved_questions",
        lambda database, session_id: [],
    )

    async def fake_generator(code, facts, **kwargs):
        assert code == submission.code
        assert kwargs["total_questions"] == 5
        assert kwargs["avoid_hashes"] == set()

        yield {
            "id": "generated-q1",
            "type": "design_decision",
            "prompt": "Why is this approach used?",
            "line_refs": [1],
            "answer_format": "free_text",
            "options": None,
            "answer_key": "sample-key",
            "explanation": "Practice-only explanation.",
            "max_score": 10,
            "question_hash": "hash-q1",
        }

    monkeypatch.setattr(
        routes,
        "_load_practice_generator",
        lambda: fake_generator,
    )

    response = asyncio.run(routes.stream_practice(session.id, user, db))
    body = collect_response(response)

    assert "event: question\n" in body
    assert "event: done\n" in body
    assert '"answer_key":"sample-key"' in body
    assert '"explanation":"Practice-only explanation."' in body
    assert session.status == "ready"

    saved = [
        item for item in db.added if isinstance(item, PracticeQuestion)
    ]
    assert len(saved) == 1
    assert saved[0].question_hash == "hash-q1"
    assert saved[0].order_idx == 1


def test_stream_emits_safe_error_and_marks_session_failed(monkeypatch):
    student_id = uuid4()
    submission = make_submission(student_id)
    session = make_session(student_id, submission.id)
    db = FakeDB(submission=submission)
    user = SimpleNamespace(id=student_id)

    monkeypatch.setattr(
        routes,
        "get_student_practice_session_or_404",
        lambda database, session_id, requested_student_id: session,
    )
    monkeypatch.setattr(
        routes,
        "_load_saved_questions",
        lambda database, session_id: [],
    )

    async def failing_generator(code, facts, **kwargs):
        raise RuntimeError("private internal failure")
        yield {}

    monkeypatch.setattr(
        routes,
        "_load_practice_generator",
        lambda: failing_generator,
    )

    response = asyncio.run(routes.stream_practice(session.id, user, db))
    body = collect_response(response)

    assert "event: error\n" in body
    assert "GENERATION_FAILED" in body
    assert "private internal failure" not in body
    assert session.status == "failed"
    assert db.rollbacks >= 1


def test_ready_session_replays_saved_question_without_regenerating(monkeypatch):
    student_id = uuid4()
    submission = make_submission(student_id)
    session = make_session(student_id, submission.id, status="ready")
    db = FakeDB(submission=submission)
    user = SimpleNamespace(id=student_id)

    saved_question = SimpleNamespace(
        id=uuid4(),
        order_idx=1,
        type="design_decision",
        prompt="Why is this approach used?",
        line_refs=[1],
        answer_format="free_text",
        options=None,
        answer_key={"__codeviva_scalar__": "previous answer"},
        explanation="Saved practice explanation.",
        question_hash="saved-hash-1",
    )

    monkeypatch.setattr(
        routes,
        "get_student_practice_session_or_404",
        lambda database, session_id, requested_student_id: session,
    )
    monkeypatch.setattr(
        routes,
        "_load_saved_questions",
        lambda database, session_id: [saved_question],
    )

    def should_not_generate():
        raise AssertionError(
            "A ready session must replay saved questions without regenerating."
        )

    monkeypatch.setattr(
        routes,
        "_load_practice_generator",
        should_not_generate,
    )

    response = asyncio.run(routes.stream_practice(session.id, user, db))
    body = collect_response(response)

    assert body.count("event: question\n") == 1
    assert "event: done\n" in body
    assert '"count":1' in body
    assert "Why is this approach used?" in body
    assert "Saved practice explanation." in body
    assert "previous answer" in body
