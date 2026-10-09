"""Teacher-owned result reads and SQL-backed lightweight analytics."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    Answer,
    AttemptResult,
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamSlot,
    Profile,
    Score,
    SlotStudent,
)
from app.schemas.teacher_results import (
    QuestionAnalyticsItem,
    QuestionAnalyticsResponse,
    ResultAnalyticsSummary,
    TeacherAttemptResultResponse,
    TeacherQuestionResult,
    TeacherResultListItem,
    TeacherResultListResponse,
)


def _result_status(result: AttemptResult | None) -> str:
    return result.status if result is not None else "pending"


def _list_item(
    attempt: ExamAttempt,
    result: AttemptResult | None,
    student: Profile,
    slot: ExamSlot,
) -> TeacherResultListItem:
    return TeacherResultListItem(
        attempt_id=attempt.id,
        student_id=student.id,
        student_email=student.email,
        student_name=student.full_name,
        exam_id=slot.exam_id,
        slot_id=slot.id,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        submitted_at=attempt.submitted_at,
        auto_submitted=attempt.auto_submitted,
        grading_status=_result_status(result),
        total_score=result.total_score if result else None,
        max_score=result.max_score if result else None,
        percentage=result.percentage if result else None,
        graded_at=result.graded_at if result else None,
    )


def list_teacher_results(
    db: Session,
    teacher_id: UUID,
    *,
    exam_id: UUID | None,
    slot_id: UUID | None,
    student_id: UUID | None,
    grading_status: str | None,
    limit: int,
    offset: int,
) -> TeacherResultListResponse:
    statement = (
        select(ExamAttempt, AttemptResult, Profile, ExamSlot)
        .join(ExamSlot, ExamSlot.id == ExamAttempt.slot_id)
        .join(Exam, Exam.id == ExamSlot.exam_id)
        .join(Profile, Profile.id == ExamAttempt.student_id)
        .outerjoin(AttemptResult, AttemptResult.attempt_id == ExamAttempt.id)
        .where(Exam.teacher_id == teacher_id)
        .order_by(ExamAttempt.started_at.desc(), ExamAttempt.id)
    )
    if exam_id is not None:
        statement = statement.where(Exam.id == exam_id)
    if slot_id is not None:
        statement = statement.where(ExamSlot.id == slot_id)
    if student_id is not None:
        statement = statement.where(ExamAttempt.student_id == student_id)
    if grading_status is not None:
        if grading_status == "pending":
            statement = statement.where(
                or_(AttemptResult.attempt_id.is_(None), AttemptResult.status == "pending")
            )
        else:
            statement = statement.where(AttemptResult.status == grading_status)
    rows = db.execute(statement.limit(limit).offset(offset)).all()
    return TeacherResultListResponse(
        items=[_list_item(*row) for row in rows], limit=limit, offset=offset
    )


def get_teacher_attempt_result(
    db: Session, teacher_id: UUID, attempt_id: UUID
) -> TeacherAttemptResultResponse | None:
    row = db.execute(
        select(ExamAttempt, AttemptResult, Profile, ExamSlot)
        .join(ExamSlot, ExamSlot.id == ExamAttempt.slot_id)
        .join(Exam, Exam.id == ExamSlot.exam_id)
        .join(Profile, Profile.id == ExamAttempt.student_id)
        .outerjoin(AttemptResult, AttemptResult.attempt_id == ExamAttempt.id)
        .where(ExamAttempt.id == attempt_id, Exam.teacher_id == teacher_id)
    ).first()
    if row is None:
        return None
    attempt, result, student, slot = row
    item = _list_item(attempt, result, student, slot)
    question_rows = db.execute(
        select(
            ExamQuestion.id,
            ExamQuestion.order_idx,
            ExamQuestion.type,
            ExamQuestion.max_score,
            Score.score,
            Score.feedback,
        )
        .outerjoin(
            Answer,
            and_(
                Answer.question_id == ExamQuestion.id,
                Answer.attempt_id == attempt.id,
            ),
        )
        .outerjoin(Score, Score.answer_id == Answer.id)
        .where(
            ExamQuestion.slot_id == attempt.slot_id,
            ExamQuestion.student_id == attempt.student_id,
            ExamQuestion.status == "approved",
        )
        .order_by(ExamQuestion.order_idx)
    ).all()
    return TeacherAttemptResultResponse(
        **item.model_dump(),
        questions=[
            TeacherQuestionResult(
                question_id=question_id,
                order_idx=order_idx,
                question_type=question_type,
                max_score=max_score,
                awarded_score=awarded_score,
                feedback=feedback,
            )
            for question_id, order_idx, question_type, max_score, awarded_score, feedback in question_rows
        ],
    )


def _analytics_summary(
    db: Session, *, exam_id: UUID, slot_id: UUID | None
) -> ResultAnalyticsSummary:
    slot_filter = [ExamSlot.exam_id == exam_id]
    if slot_id is not None:
        slot_filter.append(ExamSlot.id == slot_id)
    assigned = db.scalar(
        select(func.count(func.distinct(SlotStudent.student_id)))
        .join(ExamSlot, ExamSlot.id == SlotStudent.slot_id)
        .where(*slot_filter)
    )
    base = select(ExamAttempt.id).join(ExamSlot, ExamSlot.id == ExamAttempt.slot_id).where(*slot_filter)
    started = db.scalar(select(func.count()).select_from(base.subquery()))
    submitted = db.scalar(
        select(func.count()).select_from(
            base.where(ExamAttempt.submitted_at.is_not(None)).subquery()
        )
    )
    auto_submitted = db.scalar(
        select(func.count()).select_from(
            base.where(ExamAttempt.submitted_at.is_not(None), ExamAttempt.auto_submitted.is_(True)).subquery()
        )
    )
    normal_submitted = db.scalar(
        select(func.count()).select_from(
            base.where(ExamAttempt.submitted_at.is_not(None), ExamAttempt.auto_submitted.is_(False)).subquery()
        )
    )
    result_base = (
        select(
            AttemptResult.status,
            AttemptResult.total_score,
            AttemptResult.percentage,
        )
        .join(ExamAttempt, ExamAttempt.id == AttemptResult.attempt_id)
        .join(ExamSlot, ExamSlot.id == ExamAttempt.slot_id)
        .where(*slot_filter)
    )
    pending = db.scalar(
        select(func.count()).select_from(result_base.where(AttemptResult.status.in_(("pending", "grading"))).subquery())
    )
    graded = db.scalar(
        select(func.count()).select_from(result_base.where(AttemptResult.status == "graded").subquery())
    )
    failed = db.scalar(
        select(func.count()).select_from(result_base.where(AttemptResult.status == "failed").subquery())
    )
    graded_results = result_base.where(AttemptResult.status == "graded").subquery()
    aggregates = db.execute(
        select(
            func.avg(graded_results.c.total_score),
            func.avg(graded_results.c.percentage),
            func.max(graded_results.c.total_score),
            func.min(graded_results.c.total_score),
        )
    ).one()
    assigned_count = int(assigned or 0)
    submitted_count = int(submitted or 0)
    return ResultAnalyticsSummary(
        exam_id=exam_id,
        slot_id=slot_id,
        assigned_students=assigned_count,
        started_attempts=int(started or 0),
        submitted_attempts=submitted_count,
        auto_submitted_attempts=int(auto_submitted or 0),
        normal_submitted_attempts=int(normal_submitted or 0),
        pending_results=int(pending or 0),
        graded_results=int(graded or 0),
        failed_results=int(failed or 0),
        average_score=aggregates[0],
        average_percentage=aggregates[1],
        highest_score=aggregates[2],
        lowest_score=aggregates[3],
        submission_rate=(Decimal(submitted_count) / Decimal(assigned_count)) * Decimal(100) if assigned_count else None,
    )


def get_exam_analytics(db: Session, exam_id: UUID) -> ResultAnalyticsSummary:
    return _analytics_summary(db, exam_id=exam_id, slot_id=None)


def get_slot_analytics(db: Session, exam_id: UUID, slot_id: UUID) -> ResultAnalyticsSummary:
    return _analytics_summary(db, exam_id=exam_id, slot_id=slot_id)


def get_question_analytics(
    db: Session, *, exam_id: UUID, slot_id: UUID | None
) -> QuestionAnalyticsResponse:
    filters = [ExamQuestion.exam_id == exam_id, ExamQuestion.status == "approved"]
    if slot_id is not None:
        filters.append(ExamQuestion.slot_id == slot_id)
    rows = db.execute(
        select(
            ExamQuestion.id,
            ExamQuestion.order_idx,
            ExamQuestion.type,
            ExamQuestion.max_score,
            func.count(Answer.id),
            func.count(Score.id),
            func.avg(Score.score),
            func.avg((Score.score / func.nullif(Score.max_score, 0)) * 100),
        )
        .outerjoin(Answer, Answer.question_id == ExamQuestion.id)
        .outerjoin(Score, Score.answer_id == Answer.id)
        .where(*filters)
        .group_by(
            ExamQuestion.id,
            ExamQuestion.order_idx,
            ExamQuestion.type,
            ExamQuestion.max_score,
        )
        .order_by(ExamQuestion.order_idx, ExamQuestion.id)
    ).all()
    return QuestionAnalyticsResponse(
        exam_id=exam_id,
        slot_id=slot_id,
        questions=[
            QuestionAnalyticsItem(
                question_id=question_id,
                order_idx=order_idx,
                question_type=question_type,
                max_score=max_score,
                answered_count=answered_count,
                graded_count=graded_count,
                average_awarded_score=average_score,
                average_percentage=average_percentage,
            )
            for question_id, order_idx, question_type, max_score, answered_count, graded_count, average_score, average_percentage in rows
        ],
    )
