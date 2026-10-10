from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, func, select

from app.core.config import settings
from app.core.deps import DBSession, StudentUser
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
    CodeReviewResponse,
    StudentAnswerCreate,
    StudentAnswerResponse,
    StudentAssignmentDetailResponse,
    StudentAssignmentResponse,
    StudentAttemptDetailResponse,
    StudentAttemptResponse,
    StudentAttemptResultResponse,
    StudentQuestionResponse,
)
from app.services.ai_assignment_service import evaluate_attempt
from app.services.assignment_workflow import (
    get_student_assignment_context,
    split_assignment_description,
)

router = APIRouter(
    prefix="/student/assignments",
    tags=["student assignments"],
)


def _student_question_hint(line_refs: list[dict]) -> str:
    line_numbers = sorted(
        {
            line
            for reference in line_refs
            if isinstance(reference, dict)
            and isinstance((line := reference.get("line")), int)
            and line > 0
        }
    )
    if line_numbers:
        locations = ", ".join(str(line) for line in line_numbers)
        return (
            f"Start by reviewing line(s) {locations}. Trace how the values "
            "there lead to the behavior asked about."
        )
    return (
        "Hint: Find the relevant function, then trace its inputs through "
        "the code to the value or behavior the question asks about."
    )


def _student_assignment_response(
    db: DBSession,
    assignment: Assignment,
    slot: ExamSlot,
    group: Group,
    teacher_name: str,
    student_id: UUID,
) -> StudentAssignmentResponse:
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
    released_questions = db.scalars(
        select(ExamQuestion)
        .where(
            ExamQuestion.slot_id == slot.id,
            ExamQuestion.student_id == student_id,
            ExamQuestion.status == "approved",
        )
        .order_by(ExamQuestion.order_idx)
    ).all()
    released_count = len(released_questions)
    description, instructions = split_assignment_description(
        assignment.description
    )
    now = datetime.now(UTC)
    current_status = (
        "Completed"
        if attempt is not None and attempt.submitted_at is not None
        else "Submitted"
        if submission is not None
        else "Past due"
        if assignment.due_at is not None and assignment.due_at <= now
        else "Upcoming"
        if slot.starts_at > now
        else "Available"
    )
    return StudentAssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        description=description,
        instructions=instructions,
        language=assignment.language,
        created_at=assignment.created_at,
        due_at=assignment.due_at,
        teacher_name=teacher_name,
        group_name=group.name,
        slot_id=slot.id,
        status=current_status,
        submission_id=submission.id if submission else None,
        submission_filename=submission.filename if submission else None,
        submitted_at=submission.created_at if submission else None,
        questions_released=released_count > 0,
        question_count=released_count,
        questions=[
            StudentQuestionResponse(
                id=question.id,
                order_idx=question.order_idx,
                type=question.type,
                prompt=question.prompt,
                hint=_student_question_hint(question.line_refs or []),
                line_refs=question.line_refs,
                answer_format=question.answer_format,
                options=question.options,
            )
            for question in released_questions
        ],
        code_review=(
            CodeReviewResponse.model_validate(
                submission.code_facts.get("ai_review")
            )
            if submission is not None
            and submission.code_facts
            and submission.code_facts.get("ai_review")
            else None
        ),
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
    )


@router.get("", response_model=list[StudentAssignmentResponse])
def list_assignments(
    current_user: StudentUser,
    db: DBSession,
) -> list[StudentAssignmentResponse]:
    rows = db.execute(
        select(Assignment, ExamSlot, Group, Profile.full_name)
        .join(Exam, Exam.assignment_id == Assignment.id)
        .join(ExamSlot, ExamSlot.exam_id == Exam.id)
        .join(Group, Group.id == ExamSlot.group_id)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .join(Profile, Profile.id == Assignment.teacher_id)
        .where(GroupMember.student_id == current_user.id)
        .order_by(Assignment.created_at.desc())
    ).all()
    return [
        _student_assignment_response(
            db,
            assignment,
            slot,
            group,
            teacher_name,
            current_user.id,
        )
        for assignment, slot, group, teacher_name in rows
    ]


@router.get(
    "/{assignment_id}",
    response_model=StudentAssignmentDetailResponse,
)
def get_assignment(
    assignment_id: UUID,
    current_user: StudentUser,
    db: DBSession,
) -> StudentAssignmentDetailResponse:
    assignment, _exam, slot, group = get_student_assignment_context(
        db,
        assignment_id,
        current_user.id,
    )
    teacher_name = db.scalar(
        select(Profile.full_name).where(Profile.id == assignment.teacher_id)
    ) or "Teacher"
    summary = _student_assignment_response(
        db,
        assignment,
        slot,
        group,
        teacher_name,
        current_user.id,
    )
    return StudentAssignmentDetailResponse(
        **summary.model_dump(),
        submission_code=(
            db.scalar(
                select(Submission.code)
                .where(
                    Submission.assignment_id == assignment.id,
                    Submission.student_id == current_user.id,
                )
                .order_by(Submission.created_at.desc())
                .limit(1)
            )
        ),
    )


@router.post(
    "/{assignment_id}/attempts",
    response_model=StudentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_attempt(
    assignment_id: UUID,
    current_user: StudentUser,
    db: DBSession,
) -> StudentAttemptResponse:
    assignment, exam, slot, _group = get_student_assignment_context(
        db,
        assignment_id,
        current_user.id,
    )
    now = datetime.now(UTC)
    if slot.starts_at > now or slot.ends_at <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assignment is not currently open for questions.",
        )
    released_count = db.scalar(
        select(func.count())
        .select_from(ExamQuestion)
        .where(
            ExamQuestion.slot_id == slot.id,
            ExamQuestion.student_id == current_user.id,
            ExamQuestion.status == "approved",
        )
    ) or 0
    if not released_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your teacher has not released questions for this assignment.",
        )
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.slot_id == slot.id,
            ExamAttempt.student_id == current_user.id,
        )
    )
    if attempt is None:
        if assignment.due_at is not None and assignment.due_at <= now:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The deadline for this assignment has passed.",
            )
        attempt = ExamAttempt(
            slot_id=slot.id,
            student_id=current_user.id,
            deadline_at=min(
                now.replace(microsecond=0)
                + timedelta(minutes=exam.duration_minutes),
                slot.ends_at,
            ),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    return StudentAttemptResponse(
        id=attempt.id,
        slot_id=attempt.slot_id,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        submitted_at=attempt.submitted_at,
        auto_submitted=attempt.auto_submitted,
    )


@router.get(
    "/{assignment_id}/attempt",
    response_model=StudentAttemptDetailResponse | None,
)
def get_current_attempt(
    assignment_id: UUID,
    current_user: StudentUser,
    db: DBSession,
) -> StudentAttemptDetailResponse | None:
    _assignment, _exam, slot, _group = get_student_assignment_context(
        db,
        assignment_id,
        current_user.id,
    )
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.slot_id == slot.id,
            ExamAttempt.student_id == current_user.id,
        )
    )
    if attempt is None:
        return None
    answers = db.execute(
        select(Answer, Score)
        .outerjoin(Score, Score.answer_id == Answer.id)
        .join(ExamQuestion, ExamQuestion.id == Answer.question_id)
        .where(
            Answer.attempt_id == attempt.id,
            ExamQuestion.status == "approved",
        )
        .order_by(Answer.saved_at)
    ).all()
    attempt_result = db.scalar(
        select(AttemptResult).where(AttemptResult.attempt_id == attempt.id)
    )
    return StudentAttemptDetailResponse(
        attempt=StudentAttemptResponse(
            id=attempt.id,
            slot_id=attempt.slot_id,
            started_at=attempt.started_at,
            deadline_at=attempt.deadline_at,
            submitted_at=attempt.submitted_at,
            auto_submitted=attempt.auto_submitted,
        ),
        answers=[
            StudentAnswerResponse(
                id=answer.id,
                question_id=answer.question_id,
                answer_text=answer.answer_text,
                saved_at=answer.saved_at,
                score=score.score if score else None,
                max_score=score.max_score if score else None,
                evidence=score.evidence if score else None,
                feedback=score.feedback if score else None,
                needs_review=score.needs_review if score else None,
            )
            for answer, score in answers
        ],
        attempt_result=(
            StudentAttemptResultResponse(
                comprehension_index=attempt_result.comprehension_index,
                needs_review_count=attempt_result.needs_review_count,
                computed_at=attempt_result.computed_at,
            )
            if attempt_result is not None
            else None
        ),
    )


@router.put(
    "/{assignment_id}/attempts/{attempt_id}/answers",
    response_model=StudentAnswerResponse,
)
def save_answer(
    assignment_id: UUID,
    attempt_id: UUID,
    payload: StudentAnswerCreate,
    current_user: StudentUser,
    db: DBSession,
) -> StudentAnswerResponse:
    _assignment, _exam, slot, _group = get_student_assignment_context(
        db,
        assignment_id,
        current_user.id,
    )
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id,
            ExamAttempt.slot_id == slot.id,
            ExamAttempt.student_id == current_user.id,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if (
        attempt.submitted_at is not None
        or attempt.deadline_at <= datetime.now(UTC)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This attempt is no longer accepting answers.",
        )
    question = db.scalar(
        select(ExamQuestion).where(
            ExamQuestion.id == payload.question_id,
            ExamQuestion.slot_id == slot.id,
            ExamQuestion.student_id == current_user.id,
            ExamQuestion.status == "approved",
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found.")
    answer = db.scalar(
        select(Answer).where(
            Answer.attempt_id == attempt.id,
            Answer.question_id == question.id,
        )
    )
    if answer is None:
        answer = Answer(
            attempt_id=attempt.id,
            question_id=question.id,
            answer_text=payload.answer_text,
        )
        db.add(answer)
    else:
        answer.answer_text = payload.answer_text
    db.commit()
    db.refresh(answer)
    return StudentAnswerResponse(
        id=answer.id,
        question_id=answer.question_id,
        answer_text=answer.answer_text,
        saved_at=answer.saved_at,
    )


@router.post(
    "/{assignment_id}/attempts/{attempt_id}/submit",
    response_model=StudentAttemptResponse,
)
def submit_attempt(
    assignment_id: UUID,
    attempt_id: UUID,
    current_user: StudentUser,
    db: DBSession,
) -> StudentAttemptResponse:
    assignment, _exam, slot, _group = get_student_assignment_context(
        db,
        assignment_id,
        current_user.id,
    )
    attempt = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.id == attempt_id,
            ExamAttempt.slot_id == slot.id,
            ExamAttempt.student_id == current_user.id,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if attempt.submitted_at is None:
        answer_rows = db.execute(
            select(ExamQuestion, Answer)
            .outerjoin(
                Answer,
                and_(
                    Answer.attempt_id == attempt.id,
                    Answer.question_id == ExamQuestion.id,
                ),
            )
            .where(
                ExamQuestion.slot_id == slot.id,
                ExamQuestion.student_id == current_user.id,
                ExamQuestion.status == "approved",
            )
            .order_by(ExamQuestion.order_idx)
        ).all()
        if not answer_rows:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="There are no released questions to submit.",
            )
        source = db.scalar(
            select(Submission)
            .where(
                Submission.assignment_id == assignment.id,
                Submission.student_id == current_user.id,
            )
            .order_by(Submission.created_at.desc())
            .limit(1)
        )
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Submit code before answering the assignment questions.",
            )

        nonempty_answers = [
            {
                "question_id": str(question.id),
                "prompt": question.prompt,
                "answer_text": answer.answer_text.strip(),
                "expected_answer": question.answer_key or {},
                "rubric": question.rubric or {},
                "max_score": str(question.max_score),
            }
            for question, answer in answer_rows
            if answer is not None and answer.answer_text.strip()
        ]
        graded = evaluate_attempt(
            source_code=source.code,
            language=assignment.language,
            answers=nonempty_answers,
        ) if nonempty_answers else None
        grades = {
            item.question_id: item
            for item in graded.evaluations
        } if graded is not None else {}

        total_score = Decimal(0)
        total_max_score = Decimal(0)
        needs_review_count = 0
        sub_scores = {}
        for question, answer in answer_rows:
            if answer is None:
                answer = Answer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    answer_text="",
                )
                db.add(answer)
                db.flush()
            evaluation = grades.get(str(question.id))
            if evaluation is None:
                score_value = Decimal(0)
                confidence = Decimal(1)
                evidence = "No answer was submitted."
                feedback = (
                    "Review the released question and write an explanation "
                    "that shows your reasoning."
                )
                needs_review = False
            else:
                score_value = evaluation.score
                confidence = evaluation.confidence
                evidence = evaluation.evidence
                feedback = evaluation.feedback
                needs_review = (
                    float(confidence) < settings.confidence_review_threshold
                )
            total_score += score_value
            total_max_score += question.max_score
            needs_review_count += int(needs_review)
            sub_scores[str(question.id)] = {
                "score": str(score_value),
                "max_score": str(question.max_score),
            }
            db.add(
                Score(
                    answer_id=answer.id,
                    score=score_value,
                    max_score=question.max_score,
                    evidence=evidence,
                    confidence=confidence,
                    needs_review=needs_review,
                    feedback=feedback,
                )
            )
        comprehension_index = (
            total_score * Decimal(100) / total_max_score
        ).quantize(Decimal("0.01"))
        db.add(
            AttemptResult(
                attempt_id=attempt.id,
                comprehension_index=comprehension_index,
                sub_scores=sub_scores,
                flag_oral_followup=False,
                needs_review_count=needs_review_count,
            )
        )
        attempt.submitted_at = datetime.now(UTC)
        db.commit()
        db.refresh(attempt)
    return StudentAttemptResponse(
        id=attempt.id,
        slot_id=attempt.slot_id,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        submitted_at=attempt.submitted_at,
        auto_submitted=attempt.auto_submitted,
    )
