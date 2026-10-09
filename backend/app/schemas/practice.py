"""Request and response models for the student practice API."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


PracticeStatus = Literal["generating", "ready", "failed"]


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