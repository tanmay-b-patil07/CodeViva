"""Configurable, offline comprehension-index calculation."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .schemas import ComprehensionResult, QuestionDraft, Score

DEFAULT_CONFIG_PATH = Path(__file__).with_name("scoring_config.json")


class ScoringConfigError(ValueError):
    """Raised for invalid scoring policy configuration."""


class CategoryMappingError(ValueError):
    """Raised when a question type has no approved scoring category."""


def load_scoring_config(path: Path | str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the versioned scoring policy."""
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
        weights = config["weights"]
        mapping = config["question_type_categories"]
        followup = config["oral_followup"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ScoringConfigError("Scoring configuration is invalid") from exc
    required = {"trace", "design", "explanation", "complexity"}
    if set(weights) != required or not isinstance(mapping, dict):
        raise ScoringConfigError("Scoring configuration has missing categories")
    if any(not isinstance(value, (int, float)) or value < 0 for value in weights.values()):
        raise ScoringConfigError("Scoring weights must be non-negative numbers")
    if sum(weights.values()) <= 0:
        raise ScoringConfigError("Scoring weights must have a positive total")
    if not isinstance(followup.get("index_below"), (int, float)):
        raise ScoringConfigError("Follow-up index threshold is invalid")
    if any(category not in required for category in mapping.values()):
        raise ScoringConfigError("Question mapping contains an unknown category")
    return config


def _question_type(question: QuestionDraft | dict[str, Any]) -> str:
    return question.type if isinstance(question, QuestionDraft) else str(question["type"])


def calculate_comprehension_index(
    attempt_id: str,
    questions: Iterable[QuestionDraft | dict[str, Any]],
    scores: Iterable[Score],
    *,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
) -> ComprehensionResult:
    """Aggregate validated per-question scores without persistence or provider use."""
    config = load_scoring_config(config_path)
    score_by_id: dict[str, Score] = {}
    for score in scores:
        if score.question_id in score_by_id:
            raise ValueError("Duplicate score question_id")
        if score.max_score <= 0 or not 0 <= score.score <= score.max_score:
            raise ValueError("Score has invalid bounds")
        score_by_id[score.question_id] = score

    totals: dict[str, list[float]] = {category: [0.0, 0.0] for category in config["weights"]}
    seen_questions: set[str] = set()
    for question in questions:
        question_id = question.question_hash if isinstance(question, QuestionDraft) else question.get("question_id")
        if not question_id or question_id in seen_questions:
            raise ValueError("Question identifiers must be unique and present")
        seen_questions.add(question_id)
        category = config["question_type_categories"].get(_question_type(question))
        if category is None:
            raise CategoryMappingError(f"No scoring category for question type {_question_type(question)!r}")
        score = score_by_id.get(question_id)
        if score is None:
            continue
        totals[category][0] += score.score
        totals[category][1] += score.max_score

    percentages = {
        category: (earned / maximum) * 100
        for category, (earned, maximum) in totals.items() if maximum > 0
    }
    if not percentages:
        return ComprehensionResult(
            attempt_id=attempt_id, comprehension_index=0, sub_scores={},
            effective_weights={}, flag_oral_followup=True, needs_review_count=sum(s.needs_review for s in score_by_id.values()),
        )
    weight_total = sum(config["weights"][category] for category in percentages)
    effective = {category: config["weights"][category] / weight_total for category in percentages}
    index = sum(percentages[category] * effective[category] for category in percentages)
    index = min(max(index, 0), 100)
    return ComprehensionResult(
        attempt_id=attempt_id, comprehension_index=index, sub_scores=percentages,
        effective_weights=effective, flag_oral_followup=index < config["oral_followup"]["index_below"],
        needs_review_count=sum(score.needs_review for score in score_by_id.values()),
    )
