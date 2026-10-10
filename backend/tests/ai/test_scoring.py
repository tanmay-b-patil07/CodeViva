"""Focused offline tests for Phase 5 comprehension scoring."""

import json

import pytest

from ai.schemas import QuestionDraft, Score
from ai.scoring import (
    CategoryMappingError,
    ScoringConfigError,
    calculate_comprehension_index,
    load_scoring_config,
)


def question(question_id, question_type):
    return QuestionDraft(
        type=question_type, prompt="Question", line_refs=[1],
        answer_format="short_text", answer_key="answer", question_hash=question_id,
    )


def score(question_id, awarded, maximum=10, review=False):
    return Score(
        question_id=question_id, score=awarded, max_score=maximum,
        evidence="evidence", confidence=1, needs_review=review, feedback="feedback",
    )


def test_weighted_index_with_all_categories_and_review_count():
    questions = [
        question("trace", "trace_output"), question("design", "design_decision"),
        question("explain", "explain_line"), question("complexity", "complexity"),
    ]
    result = calculate_comprehension_index(
        "attempt", questions,
        [score("trace", 10), score("design", 8, review=True), score("explain", 6), score("complexity", 4)],
    )
    assert result.comprehension_index == pytest.approx(73)
    assert result.sub_scores == {"trace": 100, "design": 80, "explanation": 60, "complexity": 40}
    assert result.effective_weights == {"trace": 0.3, "design": 0.25, "explanation": 0.25, "complexity": 0.2}
    assert result.needs_review_count == 1


def test_missing_categories_are_renormalized_and_followup_boundary():
    result = calculate_comprehension_index("attempt", [question("trace", "trace_output"), question("design", "design_decision")], [score("trace", 0), score("design", 10)])
    assert result.effective_weights == {"trace": pytest.approx(0.3 / 0.55), "design": pytest.approx(0.25 / 0.55)}
    assert result.comprehension_index == pytest.approx(25 / 0.55)
    assert result.flag_oral_followup is True
    at_boundary = calculate_comprehension_index("attempt", [question("trace", "trace_output")], [score("trace", 5)])
    assert at_boundary.comprehension_index == 50
    assert at_boundary.flag_oral_followup is False


def test_empty_invalid_and_unmapped_inputs_are_rejected_or_safe():
    empty = calculate_comprehension_index("attempt", [], [])
    assert empty.comprehension_index == 0
    assert empty.flag_oral_followup is True
    with pytest.raises(ValueError, match="Duplicate"):
        calculate_comprehension_index("attempt", [question("q", "complexity")], [score("q", 1), score("q", 1)])
    with pytest.raises(CategoryMappingError, match="what_if"):
        calculate_comprehension_index("attempt", [question("q", "what_if")], [score("q", 1)])


def test_invalid_config_is_rejected(tmp_path):
    path = tmp_path / "scoring.json"
    path.write_text(json.dumps({"weights": {"trace": 0}, "question_type_categories": {}, "oral_followup": {"index_below": 50}}), encoding="utf-8")
    with pytest.raises(ScoringConfigError):
        load_scoring_config(path)
