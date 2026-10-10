from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import select

from app.core.authorization import (
    get_owned_assignment_or_404,
    get_owned_exam_or_404,
    get_owned_exam_slot_or_404,
    get_owned_group_or_404,
)
from app.core.deps import DBSession, TeacherUser
from app.core.errors import AppError
from app.db.models import Exam, ExamQuestion, ExamSlot, GroupMember, SlotStudent
from app.schemas.exam import (
    ExamCreate,
    ExamResponse,
    ExamSlotCreate,
    ExamSlotResponse,
    GenerationStartedResponse,
)
from app.services.generation_service import generate_for_student

router = APIRouter(prefix="/teacher/exams", tags=["teacher exams"])
slot_generation_router = APIRouter(
    prefix="/teacher/slots",
    tags=["teacher exams"],
)


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreate,
    current_user: TeacherUser,
    db: DBSession,
) -> ExamResponse:
    get_owned_assignment_or_404(db, payload.assignment_id, current_user.id)

    exam = Exam(
        teacher_id=current_user.id,
        assignment_id=payload.assignment_id,
        title=payload.title.strip(),
        duration_minutes=payload.duration_minutes,
        num_questions=payload.num_questions,
        auto_approve=payload.auto_approve,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return ExamResponse.model_validate(exam)


@router.get("", response_model=list[ExamResponse])
def list_exams(current_user: TeacherUser, db: DBSession) -> list[ExamResponse]:
    exams = db.scalars(
        select(Exam)
        .where(Exam.teacher_id == current_user.id)
        .order_by(Exam.created_at.desc())
    ).all()
    return [ExamResponse.model_validate(exam) for exam in exams]


@router.post(
    "/{exam_id}/slots",
    response_model=ExamSlotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exam_slot(
    exam_id: UUID,
    payload: ExamSlotCreate,
    current_user: TeacherUser,
    db: DBSession,
) -> ExamSlotResponse:
    get_owned_exam_or_404(db, exam_id, current_user.id)
    if payload.group_id is not None:
        get_owned_group_or_404(db, payload.group_id, current_user.id)

    slot = ExamSlot(
        exam_id=exam_id,
        group_id=payload.group_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(slot)
    db.flush()

    if payload.group_id is not None:
        student_ids = db.scalars(
            select(GroupMember.student_id).where(GroupMember.group_id == payload.group_id)
        ).all()
        db.add_all(
            SlotStudent(slot_id=slot.id, student_id=student_id, submission_id=None)
            for student_id in student_ids
        )

    db.commit()
    db.refresh(slot)
    return ExamSlotResponse.model_validate(slot)


@slot_generation_router.post(
    "/{slot_id}/generate",
    response_model=GenerationStartedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_slot_generation(
    slot_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: TeacherUser,
    db: DBSession,
) -> GenerationStartedResponse:
    get_owned_exam_slot_or_404(db, slot_id, current_user.id)
    student_ids = db.scalars(
        select(SlotStudent.student_id).where(SlotStudent.slot_id == slot_id)
    ).all()
    if not student_ids:
        raise AppError(
            code="CONFLICT",
            message="Cannot generate questions for a slot without students.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if db.scalar(select(ExamQuestion.id).where(ExamQuestion.slot_id == slot_id)) is not None:
        raise AppError(
            code="CONFLICT",
            message="Generation has already been requested for this slot.",
            status_code=status.HTTP_409_CONFLICT,
        )

    for student_id in student_ids:
        background_tasks.add_task(generate_for_student, slot_id, student_id)

    return GenerationStartedResponse(status="generation_started", queued_students=len(student_ids))
