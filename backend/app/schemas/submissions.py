from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.practice import PracticeQuestionResponse


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID | None
    filename: str
    code_hash: str
    code_facts: dict
    created_at: datetime
    ai_analysis_status: Literal["pending", "complete", "failed"] = "pending"
    ai_analysis_error: str | None = None
    practice_session_id: UUID | None = None
    practice_questions: list[PracticeQuestionResponse] = Field(default_factory=list)