from backend.analysis import (
    build_deterministic_questions,
    extract_facts,
    validate_question,
)


def test_valid_question_passes_validation():
    code = """
def greet():
    print("Hello CodeViva")

greet()
"""

    facts = extract_facts(code, "python")

    questions = build_deterministic_questions(
        code=code,
        facts=facts,
        n=3,
        seed=42,
    )

    assert questions

    problems = validate_question(
        questions[0],
        code,
        facts,
    )

    assert problems == []


def test_invalid_empty_prompt_is_rejected():
    code = """
def greet():
    print("Hello CodeViva")
"""

    facts = extract_facts(code, "python")

    questions = build_deterministic_questions(
        code=code,
        facts=facts,
        n=1,
        seed=42,
    )

    assert questions

    question = questions[0]
    question.prompt = ""

    problems = validate_question(
        question,
        code,
        facts,
    )

    assert problems


def test_invalid_line_reference_is_rejected():
    code = """
def greet():
    print("Hello CodeViva")
"""

    facts = extract_facts(code, "python")

    questions = build_deterministic_questions(
        code=code,
        facts=facts,
        n=1,
        seed=42,
    )

    assert questions

    question = questions[0]
    question.line_refs = [9999]

    problems = validate_question(
        question,
        code,
        facts,
    )

    assert problems
