"""Public request/response schemas for the student exam runtime."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentSlotResponse(BaseModel):
    slot_id: UUID
    exam_id: UUID
    exam_title: str
    assignment_id: UUID
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    attempt_id: UUID | None = None
    attempt_status: str | None = None
    has_submission: bool
    questions_ready: bool


class AttemptStartResponse(BaseModel):
    attempt_id: UUID
    deadline_at: datetime
    server_time: datetime


class QuestionPublic(BaseModel):
    """Deliberately excludes answer_key, rubric, scoring, and generation internals."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_idx: int
    type: str
    prompt: str
    line_refs: list
    answer_format: str
    options: list | None


class AnswerSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_text: str = Field(max_length=100_000)


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    attempt_id: UUID
    question_id: UUID
    answer_text: str
    saved_at: datetime


class SubmitAttemptResponse(BaseModel):
    attempt_id: UUID
    submitted_at: datetime
    auto_submitted: bool
