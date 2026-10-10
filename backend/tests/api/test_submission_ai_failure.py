from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.core.errors import AppError
from app.routers import submissions
from app.schemas.assignments import CodeSubmissionCreate


class FakeSession:
    def __init__(self):
        self.added = []
        self.commit_count = 0

    def scalar(self, _statement):
        return None

    def add(self, value):
        if value.id is None:
            value.id = uuid4()
        value.created_at = datetime.now(UTC)
        self.added.append(value)

    def commit(self):
        self.commit_count += 1

    def refresh(self, _value):
        return None

    def flush(self):
        return None


def test_submission_is_saved_when_ai_provider_fails(monkeypatch):
    source_code = "def add(a, b):\n    return a + b\n"
    db = FakeSession()

    monkeypatch.setattr(submissions, "extract_facts", lambda *_args: {
        "language": "python",
        "line_count": 2,
    })

    def fail_ai(**_kwargs):
        assert db.commit_count == 1
        raise AppError(
            code="AI_PROVIDER_ERROR",
            message="Agnes AI could not process the request. Check its API key, model, and service status.",
            status_code=502,
        )

    monkeypatch.setattr(submissions, "analyze_assignment_code", fail_ai)

    result = submissions.submit_code(
        CodeSubmissionCreate(code=source_code, language="python"),
        SimpleNamespace(id=uuid4()),
        db,
    )

    saved_submission = db.added[0]
    assert db.commit_count == 2
    assert saved_submission.code == source_code
    assert saved_submission.code_facts["ai_analysis"]["status"] == "failed"
    assert result.ai_analysis_status == "failed"
    assert result.ai_analysis_error == "Agnes AI could not process the request. Check its API key, model, and service status."
    assert result.created_at == saved_submission.created_at


def test_submission_is_saved_before_code_fact_extraction(monkeypatch):
    source_code = "print('hello')"
    db = FakeSession()

    def fail_facts(*_args):
        assert db.commit_count == 1
        raise RuntimeError("The analysis adapter is unavailable.")

    monkeypatch.setattr(submissions, "extract_facts", fail_facts)

    result = submissions.submit_code(
        CodeSubmissionCreate(code=source_code, language="python"),
        SimpleNamespace(id=uuid4()),
        db,
    )

    assert db.added[0].code == source_code
    assert db.added[0].code_facts["ai_analysis"]["status"] == "failed"
    assert result.ai_analysis_status == "failed"
    assert "code analysis could not be completed" in result.ai_analysis_error
    assert db.commit_count == 2
