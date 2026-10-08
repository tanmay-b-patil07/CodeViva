from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import DBSession, TeacherUser
from app.db.models import Assignment
from app.schemas.assignments import AssignmentCreate, AssignmentResponse


router = APIRouter(
    prefix="/teacher/assignments",
    tags=["teacher assignments"],
)


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: AssignmentCreate,
    current_user: TeacherUser,
    db: DBSession,
) -> AssignmentResponse:
    assignment = Assignment(
        teacher_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description,
        language=payload.language.strip().lower(),
        due_at=payload.due_at,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return AssignmentResponse.model_validate(assignment)


@router.get(
    "",
    response_model=list[AssignmentResponse],
)
def list_assignments(
    current_user: TeacherUser,
    db: DBSession,
) -> list[AssignmentResponse]:
    assignments = db.scalars(
        select(Assignment)
        .where(
            Assignment.teacher_id == current_user.id
        )
        .order_by(
            Assignment.created_at.desc()
        )
    ).all()

    return [
        AssignmentResponse.model_validate(assignment)
        for assignment in assignments
    ]