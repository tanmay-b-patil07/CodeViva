from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Assignment, Exam, ExamSlot, Group, GroupMember

_INSTRUCTIONS_MARKER = "\n\n--- Assignment instructions ---\n"


def compose_assignment_description(
    description: str | None,
    instructions: str | None,
) -> str | None:
    clean_description = description.strip() if description else ""
    clean_instructions = instructions.strip() if instructions else ""
    if clean_instructions:
        return clean_description + _INSTRUCTIONS_MARKER + clean_instructions
    return clean_description or None


def split_assignment_description(
    value: str | None,
) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    description, marker, instructions = value.partition(_INSTRUCTIONS_MARKER)
    return description or None, instructions if marker else None


def get_student_assignment_context(
    db: Session,
    assignment_id: UUID,
    student_id: UUID,
) -> tuple[Assignment, Exam, ExamSlot, Group]:
    row = db.execute(
        select(Assignment, Exam, ExamSlot, Group)
        .join(Exam, Exam.assignment_id == Assignment.id)
        .join(ExamSlot, ExamSlot.exam_id == Exam.id)
        .join(Group, Group.id == ExamSlot.group_id)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            Assignment.id == assignment_id,
            GroupMember.student_id == student_id,
        )
        .order_by(ExamSlot.starts_at)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )
    return row
