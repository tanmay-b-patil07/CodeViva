from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================
# CODE ANALYSIS MODELS
# ============================================================


class FunctionFact(BaseModel):
    name: str
    start_line: int
    end_line: int
    params: list[str] = Field(default_factory=list)
    is_recursive: bool = False
    cyclomatic_complexity: int = 1
    max_loop_depth: int = 0
    calls: list[str] = Field(default_factory=list)


class LoopFact(BaseModel):
    kind: str
    start_line: int
    end_line: int
    depth: int
    function: str | None = None


class EdgeCaseInput(BaseModel):
    function: str
    args: list[Any] = Field(default_factory=list)
    label: str


class CodeFacts(BaseModel):
    language: str
    code_hash: str
    line_count: int

    functions: list[FunctionFact] = Field(default_factory=list)
    loops: list[LoopFact] = Field(default_factory=list)

    data_structures: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)

    edge_case_inputs: list[EdgeCaseInput] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)


# ============================================================
# EXECUTION MODELS
# ============================================================


class RunResult(BaseModel):
    language: str
    stdout: str = ""
    stderr: str = ""

    return_value: str | None = None
    exception: str | None = None

    exit_code: int | None = None
    timed_out: bool = False

    execution_time_ms: float | None = None


# ============================================================
# TRACE MODELS
# ============================================================


class TraceStep(BaseModel):
    step: int
    line: int
    function: str | None = None

    locals: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# QUESTION MODELS
# ============================================================


QuestionType = Literal[
    "trace_output",
    "trace_variable",
    "edge_case",
    "complexity",
    "design_decision",
    "explain_line",
    "what_if",
]

AnswerFormat = Literal[
    "mcq",
    "numeric",
    "short_text",
    "free_text",
]


class QuestionPrivate(BaseModel):
    id: str

    type: QuestionType
    prompt: str

    line_refs: list[int] = Field(default_factory=list)

    answer_format: AnswerFormat

    options: list[str] | None = None

    max_score: float = 10

    answer_key: str | None = None

    rubric: dict[str, Any] | None = None

    explanation: str | None = None

    question_hash: str


class QuestionPublic(BaseModel):
    id: str
    type: QuestionType
    prompt: str
    line_refs: list[int] = Field(default_factory=list)
    answer_format: AnswerFormat
    options: list[str] | None = None
    max_score: float = 10
    question_hash: str



class QuestionValidationResult(BaseModel):
    valid: bool
    problems: list[str] = Field(default_factory=list)
