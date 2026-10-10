from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PracticeStatus = Literal["generating", "ready", "failed"]


class PracticeQuestionResponse(BaseModel):
    id: UUID
    order_idx: int
    prompt: str
    line_refs: list[dict]
    answer_text: str | None = None
    score: Decimal | None = None
    max_score: Decimal = Decimal(10)
    feedback: str | None = None
    grading_status: Literal["pending", "complete", "failed"] = "pending"


class PracticeSessionResponse(BaseModel):
    id: UUID
    status: Literal["generating", "ready", "failed"]
    created_at: datetime
    code: str
    language: str
    code_facts: dict
    questions: list[PracticeQuestionResponse]
    error: str | None = None


class PracticeAnswerCreate(BaseModel):
    answer_text: str = Field(max_length=100_000)


class PracticeAnswerResponse(BaseModel):
    question_id: UUID
    answer_text: str
    score: Decimal | None
    max_score: Decimal
    feedback: str | None
    grading_status: Literal["pending", "complete", "failed"]


class PracticeStartRequest(BaseModel):
    """Start a practice session from one of the student's submissions."""

    submission_id: UUID


class PracticeStartResponse(BaseModel):
    """Response returned when a practice session is created."""

    session_id: UUID
    status: PracticeStatus


class PracticeQuestionEvent(BaseModel):
    """Question data sent over SSE for practice mode only."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    order_idx: int = Field(ge=1)
    type: str
    prompt: str
    line_refs: list[int]
    answer_format: Literal["mcq", "numeric", "short_text", "free_text"]
    options: list[str] | None = None
    max_score: float = Field(default=10.0, gt=0)
    answer_key: str | dict | None = None
    explanation: str | None = None


class PracticeDoneEvent(BaseModel):
    """Final event sent after practice generation finishes."""

    count: int = Field(ge=0)


class PracticeErrorEvent(BaseModel):
    """Safe error details sent to a practice-stream client."""

    code: str
    message: str
