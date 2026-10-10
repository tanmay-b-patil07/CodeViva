"""Teacher-safe result and lightweight analytics response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TeacherResultListItem(BaseModel):
    attempt_id: UUID
    student_id: UUID
    student_email: str
    student_name: str
    exam_id: UUID
    slot_id: UUID
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime | None
    auto_submitted: bool
    grading_status: str
    total_score: Decimal | None = None
    max_score: Decimal | None = None
    percentage: Decimal | None = None
    graded_at: datetime | None = None


class TeacherResultListResponse(BaseModel):
    items: list[TeacherResultListItem]
    limit: int
    offset: int


class TeacherQuestionResult(BaseModel):
    question_id: UUID
    order_idx: int
    question_type: str
    awarded_score: Decimal | None = None
    max_score: Decimal
    feedback: str | None = None


class TeacherAttemptResultResponse(TeacherResultListItem):
    questions: list[TeacherQuestionResult] = Field(default_factory=list)


class ResultAnalyticsSummary(BaseModel):
    exam_id: UUID
    slot_id: UUID | None = None
    assigned_students: int
    started_attempts: int
    submitted_attempts: int
    auto_submitted_attempts: int
    normal_submitted_attempts: int
    pending_results: int
    graded_results: int
    failed_results: int
    average_score: Decimal | None = None
    average_percentage: Decimal | None = None
    highest_score: Decimal | None = None
    lowest_score: Decimal | None = None
    submission_rate: Decimal | None = None


class QuestionAnalyticsItem(BaseModel):
    question_id: UUID
    order_idx: int
    question_type: str
    max_score: Decimal
    answered_count: int
    graded_count: int
    average_awarded_score: Decimal | None = None
    average_percentage: Decimal | None = None


class QuestionAnalyticsResponse(BaseModel):
    exam_id: UUID
    slot_id: UUID | None = None
    questions: list[QuestionAnalyticsItem]
