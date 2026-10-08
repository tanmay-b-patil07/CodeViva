from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import DBSession, TeacherUser
from app.db.models import Group
from app.schemas.groups import GroupCreate, GroupResponse
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from uuid import UUID

from app.db.models import Group, GroupMember, Profile
from app.schemas.groups import (
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupResponse,
)

router = APIRouter(
    prefix="/teacher/groups",
    tags=["teacher groups"],
)


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    payload: GroupCreate,
    current_user: TeacherUser,
    db: DBSession,
) -> GroupResponse:
    group = Group(
        name=payload.name.strip(),
        teacher_id=current_user.id,
    )

    db.add(group)
    db.commit()
    db.refresh(group)

    return GroupResponse.model_validate(group)


@router.get(
    "",
    response_model=list[GroupResponse],
)
def list_groups(
    current_user: TeacherUser,
    db: DBSession,
) -> list[GroupResponse]:
    groups = db.scalars(
        select(Group)
        .where(Group.teacher_id == current_user.id)
        .order_by(Group.created_at.desc())
    ).all()

    return [
        GroupResponse.model_validate(group)
        for group in groups
    ]

@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_group_member(
    group_id: UUID,
    payload: GroupMemberAdd,
    current_user: TeacherUser,
    db: DBSession,
) -> GroupMemberResponse:
    group = db.scalar(
        select(Group).where(
            Group.id == group_id,
            Group.teacher_id == current_user.id,
        )
    )

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )

    student = db.scalar(
        select(Profile).where(
            Profile.email == payload.email,
            Profile.role == "student",
        )
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        )

    existing = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student.id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already a member of this group.",
        )

    member = GroupMember(
        group_id=group_id,
        student_id=student.id,
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return GroupMemberResponse.model_validate(member)