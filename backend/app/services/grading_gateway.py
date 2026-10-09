"""Explicit integration boundary for Member 3's exam evaluator.

Member 1 owns this stable contract.  No evaluator is bundled here: deployments
or tests replace ``grade_attempt`` when Member 3's implementation is ready.
"""

from app.schemas.grading import GradingAttemptInput, GradingResult


async def grade_attempt(payload: GradingAttemptInput) -> GradingResult:
    raise RuntimeError("Member 3 grading evaluator is not available.")
