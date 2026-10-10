from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.authorization import get_owned_group_or_404
from app.core.deps import DBSession, TeacherUser
from app.db.models import Group, GroupMember, Profile
from app.schemas.groups import (
    GroupCreate,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupResponse,
    GroupRosterStudent,
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
    group = Group(name=payload.name.strip(), teacher_id=current_user.id)
    db.add(group)
    db.commit()
    db.refresh(group)
    return GroupResponse.model_validate(group)


@router.get("", response_model=list[GroupResponse])
def list_groups(
    current_user: TeacherUser,
    db: DBSession,
) -> list[GroupResponse]:
    groups = db.scalars(
        select(Group)
        .where(Group.teacher_id == current_user.id)
        .order_by(Group.created_at.desc())
    ).all()
    return [GroupResponse.model_validate(group) for group in groups]


@router.get("/{group_id}/members", response_model=list[GroupRosterStudent])
def list_group_members(
    group_id: UUID,
    current_user: TeacherUser,
    db: DBSession,
) -> list[GroupRosterStudent]:
    group = get_owned_group_or_404(db, group_id, current_user.id)
    members = db.execute(
        select(Profile.id, Profile.full_name, Profile.email)
        .join(GroupMember, GroupMember.student_id == Profile.id)
        .where(GroupMember.group_id == group.id)
        .order_by(Profile.full_name, Profile.email)
    ).all()
    return [
        GroupRosterStudent(
            student_id=student_id,
            full_name=full_name,
            email=email,
        )
        for student_id, full_name, email in members
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
    group = get_owned_group_or_404(db, group_id, current_user.id)
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
            GroupMember.group_id == group.id,
            GroupMember.student_id == student.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already a member of this group.",
        )
    member = GroupMember(group_id=group.id, student_id=student.id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return GroupMemberResponse.model_validate(member)
