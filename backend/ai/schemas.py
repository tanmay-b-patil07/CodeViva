"""Validated data structures used at the AI boundary."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

QuestionType = Literal[
    "trace_output",
    "trace_variable",
    "edge_case",
    "complexity",
    "design_decision",
    "explain_line",
    "what_if",
]

AnswerFormat = Literal["mcq", "numeric", "short_text", "free_text"]


class Rubric(BaseModel):
    """Marking guidance for a question."""

    expected_points: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    scoring_guide: str = ""


class QuestionDraft(BaseModel):
    """Candidate question returned by a generation model."""

    model_config = ConfigDict(extra="forbid")

    type: QuestionType
    prompt: str = Field(min_length=1, max_length=1000)
    line_refs: list[int] = Field(default_factory=list)
    answer_format: AnswerFormat
    options: list[str] | None = None
    max_score: float = Field(default=10.0, gt=0)
    answer_key: str | dict[str, Any] | None = None
    rubric: Rubric | None = None
    explanation: str | None = None
    question_hash: str | None = None

    @field_validator("line_refs")
    @classmethod
    def line_numbers_must_be_positive(cls, values: list[int]) -> list[int]:
        if any(line < 1 for line in values):
            raise ValueError("Line references must be positive")
        return values

    @field_validator("options")
    @classmethod
    def mcq_options_must_be_distinct(
        cls, values: list[str] | None
    ) -> list[str] | None:
        if values is not None:
            if len(values) < 3 or len(values) > 5:
                raise ValueError("MCQ questions must have 3 to 5 options")
            if len({value.strip().casefold() for value in values}) != len(values):
                raise ValueError("MCQ options must be distinct")
        return values


class GenerationResult(BaseModel):
    """Server-side result for exam question generation."""

    questions: list[QuestionDraft]
    used_fallback: bool = False


class JudgeOutput(BaseModel):
    """Structured result from an AI rubric judge."""

    score: float = Field(ge=0)
    evidence: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    feedback: str = Field(min_length=1)


class Score(BaseModel):
    """Member 3's normalized per-question grading result."""

    question_id: str
    max_score: float = Field(gt=0)
    score: float = Field(ge=0)
    evidence: str
    confidence: float = Field(ge=0, le=1)
    needs_review: bool
    feedback: str

    @field_validator("score")
    @classmethod
    def score_cannot_exceed_max(cls, value: float, info: Any) -> float:
        maximum = info.data.get("max_score")
        if maximum is not None and value > maximum:
            raise ValueError("score cannot exceed max_score")
        return value


class ComprehensionResult(BaseModel):
    """Aggregate comprehension result, before app persistence."""

    attempt_id: str
    comprehension_index: float = Field(ge=0, le=100)
    sub_scores: dict[str, float]
    effective_weights: dict[str, float] = Field(default_factory=dict)
    flag_oral_followup: bool
    needs_review_count: int = Field(ge=0)
