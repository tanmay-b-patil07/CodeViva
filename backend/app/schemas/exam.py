from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("Datetime values must include a timezone.")
    return value


class ExamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: UUID
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(gt=0)
    num_questions: int = Field(gt=0)
    auto_approve: bool = True

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank.")
        return normalized


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    teacher_id: UUID
    assignment_id: UUID
    title: str
    duration_minutes: int
    num_questions: int
    auto_approve: bool
    created_at: datetime


class ExamSlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at")
    @classmethod
    def datetimes_must_be_timezone_aware(cls, value: datetime) -> datetime:
        return _require_timezone(value)  # type: ignore[return-value]

    @model_validator(mode="after")
    def end_must_follow_start(self) -> "ExamSlotCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at.")
        return self


class ExamSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exam_id: UUID
    group_id: UUID | None
    starts_at: datetime
    ends_at: datetime


class GenerationStartedResponse(BaseModel):
    status: str
    queued_students: int
