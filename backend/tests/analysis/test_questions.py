from backend.analysis import (
    build_deterministic_questions,
    extract_facts,
)


def test_build_trace_output_question():
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

    assert isinstance(questions, list)
    assert len(questions) > 0

    question_types = {
        question.type
        for question in questions
    }

    assert (
        "trace_output" in question_types
        or "trace_variable" in question_types
    )


def test_deterministic_generation_is_reproducible():
    code = """
def greet():
    print("Hello CodeViva")

greet()
"""

    facts = extract_facts(code, "python")

    questions_one = build_deterministic_questions(
        code=code,
        facts=facts,
        n=3,
        seed=42,
    )

    questions_two = build_deterministic_questions(
        code=code,
        facts=facts,
        n=3,
        seed=42,
    )

    assert [
        question.question_hash
        for question in questions_one
    ] == [
        question.question_hash
        for question in questions_two
    ]


def test_question_answers_are_present():
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

    for question in questions:
        assert question.prompt
        assert question.question_hash
        assert question.answer_key is not None


def test_deterministic_question_for_function_with_arguments():
    code = """
def sum_list(items):
    total = 0

    for item in items:
        total += item

    return total

sum_list([1, 2, 3])
"""

    facts = extract_facts(code, "python")

    questions = build_deterministic_questions(
        code=code,
        facts=facts,
        n=5,
        seed=42,
    )

    assert questions

    assert any(
        question.type == "edge_case"
        for question in questions
    )

    for question in questions:
        assert question.answer_key is not None
        assert question.question_hash



def test_zero_questions_returns_empty_list():
    code = """
def add(a, b):
    return a + b
"""
    facts = extract_facts(code, "python")

    result = build_deterministic_questions(
        code=code,
        facts=facts,
        n=0,
        seed=42,
    )

    assert result == []


def test_question_generation_is_deterministic():
    code = """
def add(a, b):
    return a + b
"""
    facts = extract_facts(code, "python")

    first = build_deterministic_questions(
        code=code,
        facts=facts,
        n=3,
        seed=42,
    )
    second = build_deterministic_questions(
        code=code,
        facts=facts,
        n=3,
        seed=42,
    )

    assert [q.question_hash for q in first] == [
        q.question_hash for q in second
    ]
