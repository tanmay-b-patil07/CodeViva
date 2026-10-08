from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID | None
    filename: str
    code_hash: str
    code_facts: dict
    created_at: datetime