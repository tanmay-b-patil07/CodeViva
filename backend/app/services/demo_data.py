"""Deterministic synthetic CodeViva demo data and guarded cleanup."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import (
    Answer,
    Assignment,
    AttemptResult,
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamSlot,
    Group,
    GroupMember,
    Profile,
    Score,
    SlotStudent,
    Submission,
)

DEMO_NAMESPACE = UUID("1be8daf4-bb2f-45db-a421-49bc28cef014")
DEMO_PASSWORD = "CodeViva-Demo-2026!"
DEMO_EMAILS = {
    "teacher": "teacher.demo@codeviva.local",
    "student1": "student1.demo@codeviva.local",
    "student2": "student2.demo@codeviva.local",
}


def demo_id(name: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, name)


def _get_or_create(db: Session, model, key: UUID, **values):
    instance = db.get(model, key)
    created = instance is None
    if instance is None:
        instance = model(id=key, **values)
        db.add(instance)
    else:
        for field, value in values.items():
            setattr(instance, field, value)
    return instance, created


def seed_demo_data(db: Session) -> dict[str, int]:
    """Upsert the fixed demo graph in one transaction; does not call AI services."""
    counts = {"created": 0, "reused": 0}
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        teacher, created = _get_or_create(
            db,
            Profile,
            demo_id("profile:teacher"),
            email=DEMO_EMAILS["teacher"],
            password_hash=hash_password(DEMO_PASSWORD),
            full_name="Demo Teacher",
            role="teacher",
        )
        counts["created"] += created
        counts["reused"] += not created
        # Keep a stable known development credential on reruns without
        # needlessly replacing a valid Argon2 hash each time.
        if not verify_password(DEMO_PASSWORD, teacher.password_hash):
            teacher.password_hash = hash_password(DEMO_PASSWORD)

        students = []
        for index in (1, 2):
            student, created = _get_or_create(
                db,
                Profile,
                demo_id(f"profile:student{index}"),
                email=DEMO_EMAILS[f"student{index}"],
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=f"Demo Student {index}",
                role="student",
            )
            counts["created"] += created
            counts["reused"] += not created
            if not verify_password(DEMO_PASSWORD, student.password_hash):
                student.password_hash = hash_password(DEMO_PASSWORD)
            students.append(student)
        db.flush()

        group, created = _get_or_create(
            db,
            Group,
            demo_id("group:demo-class"),
            name="CodeViva Demo Class",
            teacher_id=teacher.id,
        )
        counts["created"] += created
        counts["reused"] += not created
        for student in students:
            membership = db.get(GroupMember, (group.id, student.id))
            if membership is None:
                db.add(GroupMember(group_id=group.id, student_id=student.id))
                counts["created"] += 1
            else:
                counts["reused"] += 1
        db.flush()

        assignment, created = _get_or_create(
            db,
            Assignment,
            demo_id("assignment:basics"),
            teacher_id=teacher.id,
            title="Demo: Python Basics",
            description="Synthetic demonstration assignment; not student work.",
            language="python",
            due_at=now + timedelta(days=14),
        )
        counts["created"] += created
        counts["reused"] += not created
        db.flush()
        exam, created = _get_or_create(
            db,
            Exam,
            demo_id("exam:basics"),
            teacher_id=teacher.id,
            assignment_id=assignment.id,
            title="Demo: Code Comprehension",
            duration_minutes=30,
            num_questions=1,
            auto_approve=True,
        )
        counts["created"] += created
        counts["reused"] += not created
        db.flush()
        slot, created = _get_or_create(
            db,
            ExamSlot,
            demo_id("slot:basics"),
            exam_id=exam.id,
            group_id=group.id,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(days=7),
        )
        counts["created"] += created
        counts["reused"] += not created
        db.flush()

        attempts: list[ExamAttempt] = []
        question_ids: list[UUID] = []
        for index, student in enumerate(students, start=1):
            submission, created = _get_or_create(
                db,
                Submission,
                demo_id(f"submission:student{index}"),
                assignment_id=assignment.id,
                student_id=student.id,
                filename="demo_solution.py",
                code="value = 2 + 3\nprint(value)\n",
                code_hash=f"demo-code-hash-student-{index}-v1",
                code_facts={"demo_fixture": True},
            )
            counts["created"] += created
            counts["reused"] += not created
            db.flush()

            slot_student = db.get(SlotStudent, (slot.id, student.id))
            if slot_student is None:
                db.add(
                    SlotStudent(
                        slot_id=slot.id,
                        student_id=student.id,
                        submission_id=submission.id,
                    )
                )
                counts["created"] += 1
            else:
                slot_student.submission_id = submission.id
                counts["reused"] += 1
            db.flush()

            question, created = _get_or_create(
                db,
                ExamQuestion,
                demo_id(f"question:student{index}:1"),
                exam_id=exam.id,
                slot_id=slot.id,
                student_id=student.id,
                submission_id=submission.id,
                order_idx=1,
                type="short_answer",
                prompt="Demo question: What value does this code print?",
                line_refs=[2],
                answer_format="text",
                options=None,
                answer_key={"answer": "5"},
                rubric={
                    "points": [
                        {"description": "Identifies the output as 5", "score": 5}
                    ]
                },
                max_score=Decimal(5),
                status="approved",
                question_hash=f"demo-question-student-{index}-v1",
            )
            counts["created"] += created
            counts["reused"] += not created
            question_ids.append(question.id)

            attempt, created = _get_or_create(
                db,
                ExamAttempt,
                demo_id(f"attempt:student{index}"),
                slot_id=slot.id,
                student_id=student.id,
                started_at=now - timedelta(minutes=40),
                deadline_at=now - timedelta(minutes=10),
                submitted_at=now - timedelta(minutes=11),
                auto_submitted=index == 2,
            )
            counts["created"] += created
            counts["reused"] += not created
            attempts.append(attempt)
            # State is deliberately reset to documented demo values on reruns.
            attempt.submitted_at = now - timedelta(minutes=11)
            attempt.auto_submitted = index == 2
            db.flush()

            answer, created = _get_or_create(
                db,
                Answer,
                demo_id(f"answer:student{index}:1"),
                attempt_id=attempt.id,
                question_id=question.id,
                answer_text="5"
                if index == 1
                else "The demo answer is pending grading.",
                saved_at=now - timedelta(minutes=12),
            )
            counts["created"] += created
            counts["reused"] += not created

            result = db.get(AttemptResult, attempt.id)
            if result is None:
                result = AttemptResult(attempt_id=attempt.id, status="pending")
                db.add(result)
                counts["created"] += 1
            else:
                counts["reused"] += 1
            result.comprehension_index = None
            result.sub_scores = None
            result.flag_oral_followup = None
            result.needs_review_count = None
            result.grading_error = None
            if index == 1:
                result.status = "graded"
                result.total_score = Decimal(5)
                result.max_score = Decimal(5)
                result.percentage = Decimal(100)
                result.graded_at = now - timedelta(minutes=5)
                _score, created = _get_or_create(
                    db,
                    Score,
                    demo_id("score:student1:1"),
                    answer_id=answer.id,
                    score=Decimal(5),
                    max_score=Decimal(5),
                    evidence="Synthetic demo score; not evaluator output.",
                    confidence=Decimal(1),
                    needs_review=False,
                    feedback="Synthetic demo feedback; no evaluator was called.",
                )
                counts["created"] += created
                counts["reused"] += not created
            else:
                result.status = "pending"
                result.total_score = None
                result.max_score = None
                result.percentage = None
                result.graded_at = None

        # Defensive: remove a score if a prior partial demo state left one on the
        # pending student's answer.
        student2_answer_id = demo_id("answer:student2:1")
        db.execute(delete(Score).where(Score.answer_id == student2_answer_id))
        db.flush()
        verify_demo_data(db)
        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise


def verify_demo_data(db: Session) -> dict[str, int]:
    """Validate expected relationships and the synthetic graded/pending states."""
    teacher = db.get(Profile, demo_id("profile:teacher"))
    students = [db.get(Profile, demo_id(f"profile:student{index}")) for index in (1, 2)]
    group = db.get(Group, demo_id("group:demo-class"))
    assignment = db.get(Assignment, demo_id("assignment:basics"))
    exam = db.get(Exam, demo_id("exam:basics"))
    slot = db.get(ExamSlot, demo_id("slot:basics"))
    if (
        not teacher
        or any(student is None for student in students)
        or not group
        or not assignment
        or not exam
        or not slot
    ):
        raise RuntimeError("Demo dataset is missing a required entity.")
    if (
        exam.teacher_id != teacher.id
        or exam.assignment_id != assignment.id
        or slot.exam_id != exam.id
        or slot.group_id != group.id
    ):
        raise RuntimeError(
            "Demo dataset has an inconsistent teacher/exam/slot relationship."
        )

    for index, student in enumerate(students, start=1):
        if db.get(GroupMember, (group.id, student.id)) is None:
            raise RuntimeError("Demo group is missing a student membership.")
        membership = db.get(SlotStudent, (slot.id, student.id))
        attempt = db.get(ExamAttempt, demo_id(f"attempt:student{index}"))
        question = db.get(ExamQuestion, demo_id(f"question:student{index}:1"))
        answer = db.get(Answer, demo_id(f"answer:student{index}:1"))
        result = db.get(AttemptResult, demo_id(f"attempt:student{index}"))
        if not membership or not attempt or not question or not answer or not result:
            raise RuntimeError("Demo student workflow graph is incomplete.")
        if (
            membership.submission_id != question.submission_id
            or attempt.slot_id != slot.id
            or answer.attempt_id != attempt.id
            or answer.question_id != question.id
        ):
            raise RuntimeError(
                "Demo student workflow has an inconsistent relationship."
            )
        if question.status != "approved" or question.max_score != Decimal(5):
            raise RuntimeError("Demo question is not in the expected approved state.")
        if index == 1:
            score = db.get(Score, demo_id("score:student1:1"))
            if (
                result.status != "graded"
                or result.total_score != Decimal(5)
                or result.max_score != Decimal(5)
                or result.percentage != Decimal(100)
                or score is None
                or score.answer_id != answer.id
            ):
                raise RuntimeError("Synthetic graded demo records are inconsistent.")
        elif (
            result.status != "pending"
            or result.total_score is not None
            or db.scalar(select(Score.id).where(Score.answer_id == answer.id))
            is not None
        ):
            raise RuntimeError("Pending demo records must not contain invented scores.")
    return {
        "users": 3,
        "groups": 1,
        "assignments": 1,
        "exams": 1,
        "slots": 1,
        "attempts": 2,
    }


def assert_reset_allowed(
    *, confirm_reset: bool, environment: str, allow_reset: bool
) -> None:
    if not confirm_reset:
        raise RuntimeError("Reset refused: pass --confirm-reset explicitly.")
    if environment.lower() not in {"development", "test"}:
        raise RuntimeError("Reset refused: environment must be development or test.")
    if not allow_reset:
        raise RuntimeError(
            "Reset refused: set ALLOW_DATABASE_RESET=true for a disposable database."
        )


def reset_demo_data(
    db: Session,
    *,
    confirm_reset: bool,
    environment: str,
    allow_reset: bool,
) -> int:
    """Delete only the fixed demo graph after explicit fail-closed checks."""
    assert_reset_allowed(
        confirm_reset=confirm_reset, environment=environment, allow_reset=allow_reset
    )
    student_ids = [demo_id("profile:student1"), demo_id("profile:student2")]
    slot_id = demo_id("slot:basics")
    attempt_ids = [demo_id("attempt:student1"), demo_id("attempt:student2")]
    answer_ids = [demo_id("answer:student1:1"), demo_id("answer:student2:1")]
    submission_ids = [demo_id("submission:student1"), demo_id("submission:student2")]
    try:
        deleted = 0
        for statement in (
            delete(Score).where(Score.answer_id.in_(answer_ids)),
            delete(AttemptResult).where(AttemptResult.attempt_id.in_(attempt_ids)),
            delete(Answer).where(Answer.id.in_(answer_ids)),
            delete(ExamAttempt).where(ExamAttempt.id.in_(attempt_ids)),
            delete(ExamQuestion).where(
                ExamQuestion.id.in_(
                    [demo_id("question:student1:1"), demo_id("question:student2:1")]
                )
            ),
            delete(SlotStudent).where(
                SlotStudent.slot_id == slot_id, SlotStudent.student_id.in_(student_ids)
            ),
            delete(ExamSlot).where(ExamSlot.id == slot_id),
            delete(Submission).where(Submission.id.in_(submission_ids)),
            delete(Exam).where(Exam.id == demo_id("exam:basics")),
            delete(Assignment).where(Assignment.id == demo_id("assignment:basics")),
            delete(GroupMember).where(
                or_(
                    GroupMember.group_id == demo_id("group:demo-class"),
                    GroupMember.student_id.in_(student_ids),
                )
            ),
            delete(Group).where(Group.id == demo_id("group:demo-class")),
            delete(Profile).where(
                Profile.id.in_([demo_id("profile:teacher"), *student_ids])
            ),
        ):
            result = db.execute(statement)
            deleted += result.rowcount or 0
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise
