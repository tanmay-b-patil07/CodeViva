from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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
