from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    language: str = Field(default="python", min_length=1, max_length=50)
    due_at: datetime | None = None


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    teacher_id: UUID
    title: str
    description: str | None
    language: str
    due_at: datetime | None
    created_at: datetime