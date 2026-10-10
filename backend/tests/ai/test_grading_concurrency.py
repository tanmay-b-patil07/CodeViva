"""Offline tests for the grading service's database-claim boundary."""

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.models import ExamAttempt
from app.services import grading_service


class ClaimSession:
    """Small session double that models database claim outcomes only."""

    def __init__(self, result, *, update_count, insert_count=0, attempt=None):
        self.result = result
        self.update_count = iter((update_count,))
        self.insert_count = iter((insert_count,))
        self.attempt = attempt
        self.commits = 0

    def execute(self, _statement):
        try:
            rowcount = next(self.update_count)
        except StopIteration:
            rowcount = next(self.insert_count)
        return SimpleNamespace(rowcount=rowcount)

    def commit(self):
        self.commits += 1

    def refresh(self, _result):
        pass

    def get(self, model, _attempt_id):
        return self.attempt if model is ExamAttempt else self.result


def test_only_one_atomic_claim_owner_is_allowed_to_call_provider():
    attempt_id = uuid4()
    active = SimpleNamespace(attempt_id=attempt_id, status="grading")
    winner = ClaimSession(active, update_count=1)
    loser = ClaimSession(active, update_count=0, insert_count=0)

    winner_result, winner_owns = grading_service._claim_grading(winner, attempt_id)
    loser_result, loser_owns = grading_service._claim_grading(loser, attempt_id)

    assert winner_result is active and winner_owns is True
    assert loser_result is active and loser_owns is False
    assert winner.commits == loser.commits == 1


def test_active_claim_short_circuits_before_the_provider(monkeypatch):
    attempt_id = uuid4()
    active = SimpleNamespace(attempt_id=attempt_id, status="grading")
    attempt = SimpleNamespace(id=attempt_id, submitted_at=object())
    session = ClaimSession(active, update_count=0, insert_count=0, attempt=attempt)

    def provider_must_not_run(_payload):
        raise AssertionError("active grading operation must not call the provider")

    monkeypatch.setattr(grading_service, "_gateway_result", provider_must_not_run)

    assert grading_service.grade_submitted_attempt(session, attempt_id) is active


def test_completed_result_is_returned_without_a_second_claim_or_provider(monkeypatch):
    attempt_id = uuid4()
    completed = SimpleNamespace(attempt_id=attempt_id, status="graded")
    attempt = SimpleNamespace(id=attempt_id, submitted_at=object())
    session = ClaimSession(completed, update_count=0, insert_count=0, attempt=attempt)
    monkeypatch.setattr(
        grading_service,
        "_gateway_result",
        lambda _payload: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert grading_service.grade_submitted_attempt(session, attempt_id) is completed


def test_failure_update_does_not_overwrite_a_completed_result():
    attempt_id = uuid4()
    completed = SimpleNamespace(attempt_id=attempt_id, status="graded")
    session = ClaimSession(completed, update_count=0)

    assert (
        grading_service._record_grading_failure(
            session, attempt_id, RuntimeError("provider failed")
        )
        is completed
    )
    assert completed.status == "graded"
