from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    email: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'teacher')",
            name="ck_profiles_role",
        ),
    )


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    teacher_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("groups.id"),
        primary_key=True,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        primary_key=True,
    )


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    teacher_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'python'"),
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    assignment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assignments.id"),
        nullable=True,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    code_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    code_facts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index(
            "ix_submissions_student_created",
            "student_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_submissions_assignment",
            "assignment_id",
        ),
    )


# ---------------------------------------------------------------------------
# Practice
# ---------------------------------------------------------------------------


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('generating', 'ready', 'failed')",
            name="ck_practice_sessions_status",
        ),
    )


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("practice_sessions.id"),
        nullable=False,
    )

    order_idx: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    line_refs: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    answer_format: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    options: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    answer_key: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "source IN ('deterministic', 'llm')",
            name="ck_practice_questions_source",
        ),
    )


class PracticeAnswer(Base):
    __tablename__ = "practice_answers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    question_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("practice_questions.id"),
        nullable=False,
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_correct: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    score: Mapped[Decimal | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    teacher_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    assignment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assignments.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    num_questions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    auto_approve: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class ExamSlot(Base):
    __tablename__ = "exam_slots"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    exam_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exams.id"),
        nullable=False,
    )

    group_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("groups.id"),
        nullable=True,
    )

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "ends_at > starts_at",
            name="ck_exam_slots_time_window",
        ),
    )


class SlotStudent(Base):
    __tablename__ = "slot_students"

    slot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_slots.id"),
        primary_key=True,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        primary_key=True,
    )

    submission_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# Exam questions
# ---------------------------------------------------------------------------


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    exam_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exams.id"),
        nullable=False,
    )

    slot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_slots.id"),
        nullable=False,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False,
    )

    order_idx: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    line_refs: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    answer_format: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    options: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    answer_key: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    rubric: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    max_score: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('generating', 'draft', 'approved', 'failed')",
            name="ck_exam_questions_status",
        ),
        Index(
            "ix_exam_questions_slot_student_order",
            "slot_id",
            "student_id",
            "order_idx",
        ),
    )


# ---------------------------------------------------------------------------
# Exam attempts
# ---------------------------------------------------------------------------


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    slot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_slots.id"),
        nullable=False,
    )

    student_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    deadline_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    auto_submitted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    __table_args__ = (
        UniqueConstraint(
            "slot_id",
            "student_id",
            name="uq_exam_attempts_slot_student",
        ),
    )


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    attempt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_attempts.id"),
        nullable=False,
    )

    question_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_questions.id"),
        nullable=False,
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_answers_attempt_question",
        ),
    )


# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    answer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("answers.id"),
        nullable=False,
        unique=True,
    )

    score: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    max_score: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    evidence: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Attempt results
# ---------------------------------------------------------------------------


class AttemptResult(Base):
    __tablename__ = "attempt_results"

    attempt_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_attempts.id"),
        primary_key=True,
    )

    comprehension_index: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )

    sub_scores: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    flag_oral_followup: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    needs_review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
