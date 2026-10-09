"""Member 1's evaluator-neutral grading contracts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GradingAnswerInput(BaseModel):
    question_id: UUID
    answer_id: UUID | None = None
    answer_text: str | None = None


class GradingQuestionInput(BaseModel):
    id: UUID
    prompt: str
    type: str
    answer_format: str
    answer_key: dict | None = None
    rubric: dict | None = None
    max_score: Decimal
    answer: GradingAnswerInput | None = None


class GradingAttemptInput(BaseModel):
    attempt_id: UUID
    student_id: UUID
    slot_id: UUID
    questions: list[GradingQuestionInput]


class QuestionGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    awarded_score: Decimal = Field(ge=0)
    max_score: Decimal = Field(gt=0)
    feedback: str | None = None
    evidence: str | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    needs_review: bool = False


class GradingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    total_score: Decimal = Field(ge=0)
    max_score: Decimal = Field(gt=0)
    question_grades: list[QuestionGrade] = Field(default_factory=list)


class StudentQuestionResult(BaseModel):
    question_id: UUID
    awarded_score: Decimal
    max_score: Decimal
    feedback: str


class StudentAttemptResultResponse(BaseModel):
    attempt_id: UUID
    submitted_at: datetime | None
    auto_submitted: bool
    grading_status: str
    total_score: Decimal | None = None
    max_score: Decimal | None = None
    percentage: Decimal | None = None
    graded_at: datetime | None = None
    questions: list[StudentQuestionResult] = Field(default_factory=list)
