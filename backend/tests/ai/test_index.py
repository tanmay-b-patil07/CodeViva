"""Offline Phase 7 coverage for Phase 5 comprehension-index contracts."""

import json

import pytest

from ai.schemas import QuestionDraft, Score
from ai.scoring import (
    CategoryMappingError,
    ScoringConfigError,
    calculate_comprehension_index,
    load_scoring_config,
)


def question(identifier, kind):
    return QuestionDraft(
        type=kind,
        prompt="Question",
        line_refs=[1],
        answer_format="short_text",
        answer_key="a",
        question_hash=identifier,
    )


def score(identifier, value, maximum=10, review=False):
    return Score(
        question_id=identifier,
        score=value,
        max_score=maximum,
        evidence="e",
        confidence=1,
        needs_review=review,
        feedback="f",
    )


def test_documented_weights_percentages_and_review_count():
    questions = [
        question("t", "trace_output"),
        question("d", "design_decision"),
        question("e", "explain_line"),
        question("c", "complexity"),
    ]
    result = calculate_comprehension_index(
        "attempt",
        questions,
        [score("t", 10), score("d", 8, review=True), score("e", 6), score("c", 4)],
    )
    assert result.sub_scores == {
        "trace": 100,
        "design": 80,
        "explanation": 60,
        "complexity": 40,
    }
    assert result.effective_weights == {
        "trace": 0.30,
        "design": 0.25,
        "explanation": 0.25,
        "complexity": 0.20,
    }
    assert (
        result.comprehension_index == pytest.approx(73)
        and result.needs_review_count == 1
    )


def test_empty_categories_renormalize_and_followup_boundary():
    result = calculate_comprehension_index(
        "a",
        [question("t", "trace_output"), question("d", "design_decision")],
        [score("t", 0), score("d", 10)],
    )
    assert result.effective_weights["trace"] == pytest.approx(0.30 / 0.55)
    assert (
        result.comprehension_index == pytest.approx(25 / 0.55)
        and result.flag_oral_followup is True
    )
    boundary = calculate_comprehension_index(
        "a", [question("t", "trace_output")], [score("t", 5)]
    )
    assert boundary.comprehension_index == 50 and boundary.flag_oral_followup is False


def test_invalid_configuration_identifiers_mapping_and_empty_input(tmp_path):
    assert calculate_comprehension_index("a", [], []).comprehension_index == 0
    with pytest.raises(ValueError, match="identifiers"):
        calculate_comprehension_index(
            "a", [question("same", "complexity"), question("same", "complexity")], []
        )
    with pytest.raises(CategoryMappingError):
        calculate_comprehension_index("a", [question("w", "what_if")], [score("w", 1)])
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "weights": {"trace": 1},
                "question_type_categories": {},
                "oral_followup": {"index_below": 50},
            }
        )
    )
    with pytest.raises(ScoringConfigError):
        load_scoring_config(path)
