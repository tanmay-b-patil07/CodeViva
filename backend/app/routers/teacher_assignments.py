from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.authorization import get_owned_assignment_or_404, get_owned_group_or_404
from app.core.deps import DBSession, TeacherUser
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
    Submission,
)
from app.schemas.assignments import (
    AssignmentCreate,
    AssignmentStudentResponse,
    CodeReviewResponse,
    QuestionsReleasedResponse,
    TeacherAssignmentDetailResponse,
    TeacherAssignmentResponse,
    TeacherAttemptResultResponse,
    TeacherQuestionCreate,
    TeacherQuestionRelease,
    TeacherQuestionResponse,
    TeacherStudentDetailResponse,
)
from app.services.assignment_workflow import (
    compose_assignment_description,
    split_assignment_description,
)
from app.services.submissions import SUPPORTED_LANGUAGES

router = APIRouter(
    prefix="/teacher/assignments",
    tags=["teacher assignments"],
)

_NO_DEADLINE = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)


def _assignment_slot(
    db: Session,
    assignment_id: UUID,
) -> tuple[Exam, ExamSlot, Group] | None:
    return db.execute(
        select(Exam, ExamSlot, Group)
        .join(ExamSlot, ExamSlot.exam_id == Exam.id)
        .join(Group, Group.id == ExamSlot.group_id)
        .where(Exam.assignment_id == assignment_id)
        .order_by(ExamSlot.starts_at)
    ).first()


def _teacher_assignment_response(
    db: Session,
    assignment: Assignment,
) -> TeacherAssignmentResponse:
    group_id = group_name = slot_id = None
    student_count = released_questions = draft_questions = 0
    slot_data = _assignment_slot(db, assignment.id)
    if slot_data is not None:
        _exam, slot, group = slot_data
        group_id, group_name, slot_id = group.id, group.name, slot.id
        student_count = db.scalar(
            select(func.count())
            .select_from(GroupMember)
            .where(GroupMember.group_id == group.id)
        ) or 0
        released_questions = db.scalar(
            select(func.count())
            .select_from(ExamQuestion)
            .where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.status == "approved",
            )
        ) or 0
        draft_questions = db.scalar(
            select(func.count())
            .select_from(ExamQuestion)
            .where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.status == "draft",
            )
        ) or 0
    description, instructions = split_assignment_description(
        assignment.description
    )
    teacher_name = db.scalar(
        select(Profile.full_name).where(Profile.id == assignment.teacher_id)
    ) or "Teacher"
    past_due = (
        assignment.due_at is not None
        and assignment.due_at <= datetime.now(UTC)
    )
    return TeacherAssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        description=description,
        instructions=instructions,
        language=assignment.language,
        created_at=assignment.created_at,
        due_at=assignment.due_at,
        teacher_name=teacher_name,
        group_id=group_id,
        group_name=group_name,
        slot_id=slot_id,
        student_count=student_count,
        released_questions=released_questions,
        draft_questions=draft_questions,
        status="Past due" if past_due else "Active",
    )


def _assignment_students(
    db: Session,
    assignment: Assignment,
    slot: ExamSlot,
    group: Group,
) -> list[AssignmentStudentResponse]:
    members = db.execute(
        select(Profile.id, Profile.full_name, Profile.email)
        .join(GroupMember, GroupMember.student_id == Profile.id)
        .where(
            GroupMember.group_id == group.id,
            Profile.role == "student",
        )
        .order_by(Profile.full_name, Profile.email)
    ).all()
    now = datetime.now(UTC)
    result = []
    for student_id, full_name, email in members:
        submission = db.scalar(
            select(Submission)
            .where(
                Submission.assignment_id == assignment.id,
                Submission.student_id == student_id,
            )
            .order_by(Submission.created_at.desc())
            .limit(1)
        )
        attempt = db.scalar(
            select(ExamAttempt).where(
                ExamAttempt.slot_id == slot.id,
                ExamAttempt.student_id == student_id,
            )
        )
        released_count = db.scalar(
            select(func.count())
            .select_from(ExamQuestion)
            .where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.student_id == student_id,
                ExamQuestion.status == "approved",
            )
        ) or 0
        answered_count = db.scalar(
            select(func.count())
            .select_from(Answer)
            .join(ExamAttempt, ExamAttempt.id == Answer.attempt_id)
            .where(
                ExamAttempt.slot_id == slot.id,
                ExamAttempt.student_id == student_id,
            )
        ) or 0
        score, max_score, graded_count = db.execute(
            select(
                func.sum(Score.score),
                func.sum(Score.max_score),
                func.count(Score.id),
            )
            .select_from(Score)
            .join(Answer, Answer.id == Score.answer_id)
            .join(ExamAttempt, ExamAttempt.id == Answer.attempt_id)
            .where(
                ExamAttempt.slot_id == slot.id,
                ExamAttempt.student_id == student_id,
            )
        ).one()
        student_status = (
            "Completed"
            if attempt is not None and attempt.submitted_at is not None
            else "Submitted"
            if submission is not None
            else "Past due"
            if assignment.due_at is not None and assignment.due_at <= now
            else "Available"
        )
        result.append(
            AssignmentStudentResponse(
                student_id=student_id,
                full_name=full_name,
                email=email,
                submission_id=submission.id if submission else None,
                submission_filename=submission.filename if submission else None,
                submitted_at=submission.created_at if submission else None,
                status=student_status,
                released_questions=released_count,
                answered_questions=answered_count,
                score=score if graded_count else None,
                max_score=max_score if graded_count else None,
                graded_answers=graded_count or 0,
                submitted_attempt=(
                    attempt is not None and attempt.submitted_at is not None
                ),
            )
        )
    return result


@router.post(
    "",
    response_model=TeacherAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: AssignmentCreate,
    current_user: TeacherUser,
    db: DBSession,
) -> TeacherAssignmentResponse:
    language = payload.language.strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported assignment language.",
        )
    if payload.due_at is not None and payload.due_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The deadline must be in the future.",
        )
    group = get_owned_group_or_404(db, payload.group_id, current_user.id)
    assignment = Assignment(
        teacher_id=current_user.id,
        title=payload.title.strip(),
        description=compose_assignment_description(
            payload.description,
            payload.instructions,
        ),
        language=language,
        due_at=payload.due_at,
    )
    db.add(assignment)
    db.flush()
    exam = Exam(
        teacher_id=current_user.id,
        assignment_id=assignment.id,
        title=assignment.title,
        duration_minutes=payload.duration_minutes,
        num_questions=100,
        auto_approve=False,
    )
    db.add(exam)
    db.flush()
    db.add(
        ExamSlot(
            exam_id=exam.id,
            group_id=group.id,
            starts_at=datetime.now(UTC),
            ends_at=payload.due_at or _NO_DEADLINE,
        )
    )
    db.commit()
    db.refresh(assignment)
    return _teacher_assignment_response(db, assignment)


@router.get("", response_model=list[TeacherAssignmentResponse])
def list_assignments(
    current_user: TeacherUser,
    db: DBSession,
) -> list[TeacherAssignmentResponse]:
    assignments = db.scalars(
        select(Assignment)
        .where(Assignment.teacher_id == current_user.id)
        .order_by(Assignment.created_at.desc())
    ).all()
    return [
        _teacher_assignment_response(db, assignment)
        for assignment in assignments
    ]


@router.get(
    "/{assignment_id}",
    response_model=TeacherAssignmentDetailResponse,
)
def get_assignment(
    assignment_id: UUID,
    current_user: TeacherUser,
    db: DBSession,
) -> TeacherAssignmentDetailResponse:
    assignment = get_owned_assignment_or_404(
        db,
        assignment_id,
        current_user.id,
    )
    slot_data = _assignment_slot(db, assignment.id)
    if slot_data is None:
        raise HTTPException(status_code=404, detail="Assigned class not found.")
    _exam, slot, group = slot_data
    return TeacherAssignmentDetailResponse(
        assignment=_teacher_assignment_response(db, assignment),
        students=_assignment_students(db, assignment, slot, group),
    )


@router.get(
    "/{assignment_id}/students/{student_id}",
    response_model=TeacherStudentDetailResponse,
)
def get_student_assignment_detail(
    assignment_id: UUID,
    student_id: UUID,
    current_user: TeacherUser,
    db: DBSession,
) -> TeacherStudentDetailResponse:
    assignment = get_owned_assignment_or_404(
        db,
        assignment_id,
        current_user.id,
    )
    slot_data = _assignment_slot(db, assignment.id)
    if slot_data is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    _exam, slot, group = slot_data
    student = db.scalar(
        select(Profile)
        .join(GroupMember, GroupMember.student_id == Profile.id)
        .where(
            Profile.id == student_id,
            GroupMember.group_id == group.id,
            Profile.role == "student",
        )
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    student_summary = next(
        (
            row for row in _assignment_students(db, assignment, slot, group)
            if row.student_id == student_id
        ),
        None,
    )
    if student_summary is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    submission = db.scalar(
        select(Submission)
        .where(
            Submission.assignment_id == assignment.id,
            Submission.student_id == student_id,
        )
        .order_by(Submission.created_at.desc())
        .limit(1)
    )
    question_query = (
        select(ExamQuestion, Answer, Score)
        .outerjoin(
            ExamAttempt,
            and_(
                ExamAttempt.slot_id == slot.id,
                ExamAttempt.student_id == student_id,
            ),
        )
        .outerjoin(
            Answer,
            and_(
                Answer.attempt_id == ExamAttempt.id,
                Answer.question_id == ExamQuestion.id,
            ),
        )
        .outerjoin(Score, Score.answer_id == Answer.id)
        .where(
            ExamQuestion.slot_id == slot.id,
            ExamQuestion.student_id == student_id,
        )
    )
    if submission is not None:
        question_query = question_query.where(
            ExamQuestion.submission_id == submission.id
        )
    rows = db.execute(question_query.order_by(ExamQuestion.order_idx)).all()
    attempt_result = db.scalar(
        select(AttemptResult)
        .join(ExamAttempt, ExamAttempt.id == AttemptResult.attempt_id)
        .where(
            ExamAttempt.slot_id == slot.id,
            ExamAttempt.student_id == student_id,
        )
    )
    return TeacherStudentDetailResponse(
        student=student_summary,
        submission_code=submission.code if submission else None,
        code_facts=submission.code_facts if submission else None,
        ai_analysis_status=(
            submission.code_facts.get("ai_analysis", {}).get("status")
            if submission is not None and submission.code_facts
            else None
        ),
        ai_analysis_error=(
            submission.code_facts.get("ai_analysis", {}).get("message")
            if submission is not None and submission.code_facts
            else None
        ),
        code_review=(
            CodeReviewResponse.model_validate(
                submission.code_facts.get("ai_review")
            )
            if submission is not None
            and submission.code_facts
            and submission.code_facts.get("ai_review")
            else None
        ),
        answers=[
            {
                "question_id": question.id,
                "order_idx": question.order_idx,
                "prompt": question.prompt,
                "released": question.status == "approved",
                "answer_text": answer.answer_text if answer else None,
                "score": score.score if score else None,
                "max_score": question.max_score,
                "evidence": score.evidence if score else None,
                "feedback": score.feedback if score else None,
                "needs_review": score.needs_review if score else None,
            }
            for question, answer, score in rows
        ],
        attempt_result=(
            TeacherAttemptResultResponse(
                comprehension_index=attempt_result.comprehension_index,
                sub_scores=attempt_result.sub_scores,
                flag_oral_followup=attempt_result.flag_oral_followup,
                needs_review_count=attempt_result.needs_review_count,
                computed_at=attempt_result.computed_at,
            )
            if attempt_result is not None
            else None
        ),
    )


@router.post(
    "/{assignment_id}/questions",
    response_model=TeacherQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment_question(
    assignment_id: UUID,
    payload: TeacherQuestionCreate,
    current_user: TeacherUser,
    db: DBSession,
) -> TeacherQuestionResponse:
    assignment = get_owned_assignment_or_404(
        db,
        assignment_id,
        current_user.id,
    )
    slot_data = _assignment_slot(db, assignment.id)
    if slot_data is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    exam, slot, group = slot_data
    membership = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group.id,
            GroupMember.student_id == payload.student_id,
        )
    )
    submission = db.scalar(
        select(Submission).where(
            Submission.id == payload.submission_id,
            Submission.assignment_id == assignment.id,
            Submission.student_id == payload.student_id,
        )
    )
    if membership is None or submission is None:
        raise HTTPException(
            status_code=404,
            detail="Student submission not found in this assignment.",
        )
    order_idx = (
        db.scalar(
            select(func.max(ExamQuestion.order_idx)).where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.student_id == payload.student_id,
            )
        )
        or 0
    ) + 1
    hash_input = (
        payload.prompt
        + repr(payload.answer_key)
        + repr(payload.rubric)
        + str(payload.student_id)
    )
    question = ExamQuestion(
        exam_id=exam.id,
        slot_id=slot.id,
        student_id=payload.student_id,
        submission_id=submission.id,
        order_idx=order_idx,
        type=payload.type,
        prompt=payload.prompt.strip(),
        line_refs=payload.line_refs,
        answer_format=payload.answer_format,
        options=payload.options,
        answer_key=payload.answer_key,
        rubric=payload.rubric,
        max_score=payload.max_score,
        status="draft",
        question_hash="sha256:" + sha256(hash_input.encode("utf-8")).hexdigest(),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return TeacherQuestionResponse(
        id=question.id,
        student_id=question.student_id,
        prompt=question.prompt,
        order_idx=question.order_idx,
        max_score=question.max_score,
        status=question.status,
    )


@router.post(
    "/{assignment_id}/questions/release",
    response_model=QuestionsReleasedResponse,
)
def release_assignment_questions(
    assignment_id: UUID,
    current_user: TeacherUser,
    db: DBSession,
) -> QuestionsReleasedResponse:
    assignment = get_owned_assignment_or_404(
        db,
        assignment_id,
        current_user.id,
    )
    slot_data = _assignment_slot(db, assignment.id)
    if slot_data is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    _exam, slot, _group = slot_data
    questions = db.scalars(
        select(ExamQuestion).where(
            ExamQuestion.slot_id == slot.id,
            ExamQuestion.status == "draft",
        )
    ).all()
    for question in questions:
        question.status = "approved"
    db.commit()
    return QuestionsReleasedResponse(released_questions=len(questions))


@router.patch(
    "/{assignment_id}/questions/{question_id}/release",
    response_model=TeacherQuestionResponse,
)
def set_question_release(
    assignment_id: UUID,
    question_id: UUID,
    payload: TeacherQuestionRelease,
    current_user: TeacherUser,
    db: DBSession,
) -> TeacherQuestionResponse:
    assignment = get_owned_assignment_or_404(
        db,
        assignment_id,
        current_user.id,
    )
    question = db.scalar(
        select(ExamQuestion)
        .join(Exam, Exam.id == ExamQuestion.exam_id)
        .where(
            Exam.assignment_id == assignment.id,
            Exam.teacher_id == current_user.id,
            ExamQuestion.id == question_id,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    question.status = "approved" if payload.released else "draft"
    db.commit()
    db.refresh(question)
    return TeacherQuestionResponse(
        id=question.id,
        student_id=question.student_id,
        prompt=question.prompt,
        order_idx=question.order_idx,
        max_score=question.max_score,
        status=question.status,
    )
