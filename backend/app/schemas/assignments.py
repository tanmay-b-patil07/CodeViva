from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    instructions: str | None = Field(default=None, max_length=10_000)
    language: str = Field(default="python", min_length=1, max_length=50)
    group_id: UUID
    due_at: datetime | None = None
    duration_minutes: int = Field(default=480, ge=1, le=480)

    @field_validator("due_at")
    @classmethod
    def due_date_must_be_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("The deadline must include a timezone.")
        return value

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank.")
        return normalized

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("language must not be blank.")
        return normalized

class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    teacher_id: UUID
    title: str
    description: str | None
    language: str
    due_at: datetime | None
    created_at: datetime


class TeacherAssignmentResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    instructions: str | None
    language: str
    created_at: datetime
    due_at: datetime | None
    teacher_name: str
    group_id: UUID | None
    group_name: str | None
    slot_id: UUID | None
    student_count: int
    released_questions: int
    draft_questions: int = 0
    status: str


class QuestionsReleasedResponse(BaseModel):
    released_questions: int


class CodeReviewResponse(BaseModel):
    summary: str
    code_suggestions: list[str]
    understanding_suggestions: list[str]


class StudentQuestionResponse(BaseModel):
    id: UUID
    order_idx: int
    type: str
    prompt: str
    hint: str
    line_refs: list[dict]
    answer_format: str
    options: list[str] | None


class StudentAssignmentResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    instructions: str | None
    language: str
    created_at: datetime
    due_at: datetime | None
    teacher_name: str
    group_name: str
    slot_id: UUID
    status: str
    submission_id: UUID | None
    submission_filename: str | None
    submitted_at: datetime | None
    questions_released: bool
    question_count: int
    questions: list[StudentQuestionResponse] = Field(default_factory=list)
    code_review: CodeReviewResponse | None = None
    ai_analysis_status: str | None = None
    ai_analysis_error: str | None = None


class CodeSubmissionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50_000)
    language: str = Field(min_length=1, max_length=50)
    assignment_id: UUID | None = None


class AssignmentStudentResponse(BaseModel):
    student_id: UUID
    full_name: str
    email: EmailStr
    submission_id: UUID | None
    submission_filename: str | None
    submitted_at: datetime | None
    status: str
    released_questions: int
    answered_questions: int
    score: Decimal | None = None
    max_score: Decimal | None = None
    graded_answers: int = 0
    submitted_attempt: bool


class TeacherAssignmentDetailResponse(BaseModel):
    assignment: TeacherAssignmentResponse
    students: list[AssignmentStudentResponse]


class TeacherQuestionCreate(BaseModel):
    student_id: UUID
    submission_id: UUID
    prompt: str = Field(min_length=1, max_length=10_000)
    type: str = Field(default="short_answer", min_length=1, max_length=50)
    line_refs: list[dict] = Field(default_factory=list)
    answer_format: str = Field(default="text", min_length=1, max_length=100)
    options: list[str] | None = None
    answer_key: dict
    rubric: dict
    max_score: Decimal = Field(default=Decimal(1), gt=0)


class TeacherQuestionResponse(BaseModel):
    id: UUID
    student_id: UUID
    prompt: str
    order_idx: int
    max_score: Decimal
    status: str


class TeacherQuestionRelease(BaseModel):
    released: bool


class StudentAssignmentDetailResponse(StudentAssignmentResponse):
    submission_code: str | None = None


class StudentAnswerCreate(BaseModel):
    question_id: UUID
    answer_text: str = Field(max_length=100_000)


class StudentAnswerResponse(BaseModel):
    id: UUID
    question_id: UUID
    answer_text: str
    saved_at: datetime
    score: Decimal | None = None
    max_score: Decimal | None = None
    evidence: str | None = None
    feedback: str | None = None
    needs_review: bool | None = None


class StudentAttemptResponse(BaseModel):
    id: UUID
    slot_id: UUID
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime | None
    auto_submitted: bool


class StudentAttemptResultResponse(BaseModel):
    comprehension_index: Decimal
    needs_review_count: int
    computed_at: datetime


class StudentAttemptDetailResponse(BaseModel):
    attempt: StudentAttemptResponse
    answers: list[StudentAnswerResponse]
    attempt_result: StudentAttemptResultResponse | None = None


class TeacherAnswerResultResponse(BaseModel):
    question_id: UUID
    order_idx: int
    prompt: str
    released: bool
    answer_text: str | None
    score: Decimal | None
    max_score: Decimal
    evidence: str | None
    feedback: str | None
    needs_review: bool | None


class TeacherAttemptResultResponse(BaseModel):
    comprehension_index: Decimal
    sub_scores: dict
    flag_oral_followup: bool
    needs_review_count: int
    computed_at: datetime


class TeacherStudentDetailResponse(BaseModel):
    student: AssignmentStudentResponse
    submission_code: str | None
    code_facts: dict | None
    code_review: CodeReviewResponse | None = None
    ai_analysis_status: str | None = None
    ai_analysis_error: str | None = None
    answers: list[TeacherAnswerResultResponse]
    attempt_result: TeacherAttemptResultResponse | None = None
