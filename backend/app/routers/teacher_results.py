"""Teacher-owned attempt results and lightweight exam analytics."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.authorization import get_owned_exam_or_404, get_owned_exam_slot_or_404
from app.core.deps import DBSession, TeacherUser
from app.core.errors import AppError
from app.schemas.teacher_results import (
    QuestionAnalyticsResponse,
    ResultAnalyticsSummary,
    TeacherAttemptResultResponse,
    TeacherResultListResponse,
)
from app.services.teacher_results_service import (
    get_exam_analytics,
    get_question_analytics,
    get_slot_analytics,
    get_teacher_attempt_result,
    list_teacher_results,
)

router = APIRouter(prefix="/teacher", tags=["teacher results"])


@router.get("/results", response_model=TeacherResultListResponse)
def list_results(
    current_user: TeacherUser,
    db: DBSession,
    exam_id: UUID | None = None,
    slot_id: UUID | None = None,
    student_id: UUID | None = None,
    grading_status: Literal["pending", "grading", "graded", "failed"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TeacherResultListResponse:
    if exam_id is not None:
        get_owned_exam_or_404(db, exam_id, current_user.id)
    if slot_id is not None:
        get_owned_exam_slot_or_404(db, slot_id, current_user.id)
    return list_teacher_results(db, current_user.id, exam_id=exam_id, slot_id=slot_id, student_id=student_id, grading_status=grading_status, limit=limit, offset=offset)


@router.get("/results/{attempt_id}", response_model=TeacherAttemptResultResponse)
def get_result(attempt_id: UUID, current_user: TeacherUser, db: DBSession) -> TeacherAttemptResultResponse:
    result = get_teacher_attempt_result(db, current_user.id, attempt_id)
    if result is None:
        raise AppError("NOT_FOUND", "Exam attempt not found.", status.HTTP_404_NOT_FOUND)
    return result


@router.get("/exams/{exam_id}/analytics", response_model=ResultAnalyticsSummary)
def exam_analytics(exam_id: UUID, current_user: TeacherUser, db: DBSession) -> ResultAnalyticsSummary:
    get_owned_exam_or_404(db, exam_id, current_user.id)
    return get_exam_analytics(db, exam_id)


@router.get("/slots/{slot_id}/analytics", response_model=ResultAnalyticsSummary)
def slot_analytics(slot_id: UUID, current_user: TeacherUser, db: DBSession) -> ResultAnalyticsSummary:
    slot = get_owned_exam_slot_or_404(db, slot_id, current_user.id)
    return get_slot_analytics(db, slot.exam_id, slot_id)


@router.get("/exams/{exam_id}/question-analytics", response_model=QuestionAnalyticsResponse)
def exam_question_analytics(exam_id: UUID, current_user: TeacherUser, db: DBSession) -> QuestionAnalyticsResponse:
    get_owned_exam_or_404(db, exam_id, current_user.id)
    return get_question_analytics(db, exam_id=exam_id, slot_id=None)


@router.get("/slots/{slot_id}/question-analytics", response_model=QuestionAnalyticsResponse)
def slot_question_analytics(slot_id: UUID, current_user: TeacherUser, db: DBSession) -> QuestionAnalyticsResponse:
    slot = get_owned_exam_slot_or_404(db, slot_id, current_user.id)
    return get_question_analytics(db, exam_id=slot.exam_id, slot_id=slot_id)
