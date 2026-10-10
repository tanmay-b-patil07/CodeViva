from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    teacher_id: UUID
    created_at: datetime


class GroupMemberAdd(BaseModel):
    email: EmailStr


class GroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group_id: UUID
    student_id: UUID


class GroupRosterStudent(BaseModel):
    student_id: UUID
    full_name: str
    email: EmailStr