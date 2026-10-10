"""Phase 14 deterministic demo seed/reset utility tests."""

from sqlalchemy import select, text

from app.core.security import verify_password
from app.db.models import (
    AttemptResult,
    ExamAttempt,
    ExamQuestion,
    GroupMember,
    Profile,
    Score,
    SlotStudent,
)
from app.db.session import get_db
from app.services import demo_data
from app.services.demo_data import (
    DEMO_EMAILS,
    DEMO_PASSWORD,
    assert_reset_allowed,
    demo_id,
    reset_demo_data,
    seed_demo_data,
    verify_demo_data,
)


def test_seed_is_coherent_idempotent_hashed_and_resets_safely():
    db = next(get_db())
    try:
        reset_demo_data(
            db,
            confirm_reset=True,
            environment="development",
            allow_reset=True,
        )
        first = seed_demo_data(db)
        assert first["created"] > 0 and first["reused"] == 0
        graph = verify_demo_data(db)
        assert graph == {
            "users": 3,
            "groups": 1,
            "assignments": 1,
            "exams": 1,
            "slots": 1,
            "attempts": 2,
        }

        users = db.scalars(
            select(Profile).where(Profile.email.in_(DEMO_EMAILS.values()))
        ).all()
        assert len(users) == 3
        assert all(verify_password(DEMO_PASSWORD, user.password_hash) for user in users)
        assert all(user.password_hash != DEMO_PASSWORD for user in users)
        assert db.scalar(
            select(ExamQuestion.id).where(
                ExamQuestion.id == demo_id("question:student1:1")
            )
        )
        assert (
            db.scalar(
                select(AttemptResult.status).where(
                    AttemptResult.attempt_id == demo_id("attempt:student1")
                )
            )
            == "graded"
        )
        assert (
            db.scalar(
                select(AttemptResult.status).where(
                    AttemptResult.attempt_id == demo_id("attempt:student2")
                )
            )
            == "pending"
        )

        schema_version_before = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        second = seed_demo_data(db)
        assert second["created"] == 0
        assert second["reused"] > 0
        assert verify_demo_data(db) == graph
        assert (
            len(
                db.scalars(
                    select(Profile).where(Profile.email.in_(DEMO_EMAILS.values()))
                ).all()
            )
            == 3
        )
        assert (
            len(
                db.scalars(
                    select(GroupMember).where(
                        GroupMember.group_id == demo_id("group:demo-class")
                    )
                ).all()
            )
            == 2
        )
        assert (
            len(
                db.scalars(
                    select(SlotStudent).where(
                        SlotStudent.slot_id == demo_id("slot:basics")
                    )
                ).all()
            )
            == 2
        )
        assert (
            len(
                db.scalars(
                    select(ExamAttempt).where(
                        ExamAttempt.slot_id == demo_id("slot:basics")
                    )
                ).all()
            )
            == 2
        )
        assert (
            schema_version_before
            == db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        )

        assert_reset_allowed(confirm_reset=True, environment="test", allow_reset=True)
        try:
            reset_demo_data(
                db, confirm_reset=False, environment="development", allow_reset=True
            )
        except RuntimeError as exc:
            assert "--confirm-reset" in str(exc)
        else:
            raise AssertionError("Reset without explicit confirmation was accepted.")

        for unsafe_environment, allow_reset in (
            ("production", True),
            ("development", False),
        ):
            try:
                reset_demo_data(
                    db,
                    confirm_reset=True,
                    environment=unsafe_environment,
                    allow_reset=allow_reset,
                )
            except RuntimeError:
                pass
            else:
                raise AssertionError(
                    "Reset safety guard accepted an unsafe configuration."
                )

        deleted = reset_demo_data(
            db, confirm_reset=True, environment="development", allow_reset=True
        )
        assert deleted > 0
        assert db.get(Profile, demo_id("profile:teacher")) is None
        assert db.get(ExamAttempt, demo_id("attempt:student1")) is None
        assert db.get(AttemptResult, demo_id("attempt:student1")) is None
        assert db.get(Score, demo_id("score:student1:1")) is None
        assert (
            schema_version_before
            == db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        )

        seed_demo_data(db)
        assert verify_demo_data(db)["attempts"] == 2
    finally:
        reset_demo_data(
            db,
            confirm_reset=True,
            environment="development",
            allow_reset=True,
        )
        db.close()


def test_reset_guard_fails_closed_for_each_missing_requirement():
    checks = (
        (False, "development", True, "--confirm-reset"),
        (True, "production", True, "environment"),
        (True, "development", False, "ALLOW_DATABASE_RESET"),
    )
    for confirmed, environment, allowed, message in checks:
        try:
            assert_reset_allowed(
                confirm_reset=confirmed, environment=environment, allow_reset=allowed
            )
        except RuntimeError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("Unsafe reset configuration was accepted.")


def test_seed_rolls_back_all_rows_when_verification_fails(monkeypatch):
    db = next(get_db())
    try:
        reset_demo_data(db, confirm_reset=True, environment="test", allow_reset=True)

        def fail_verification(_db):
            raise RuntimeError("simulated verification failure")

        monkeypatch.setattr(demo_data, "verify_demo_data", fail_verification)
        try:
            seed_demo_data(db)
        except RuntimeError as exc:
            assert "simulated verification failure" in str(exc)
        else:
            raise AssertionError(
                "Seed unexpectedly committed after verification failed."
            )
        assert db.get(Profile, demo_id("profile:teacher")) is None
        assert db.get(Profile, demo_id("profile:student1")) is None
    finally:
        reset_demo_data(db, confirm_reset=True, environment="test", allow_reset=True)
        db.close()
