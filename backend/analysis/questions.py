from __future__ import annotations
import random

import hashlib
import json
from typing import Any

from .models import (
    CodeFacts,
    QuestionPrivate,
)
from .runner import run_code
from .tracer import trace_run


def _question_hash(
    question_type: str,
    prompt: str,
    line_refs: list[int],
) -> str:

    data = {
        "type": question_type,
        "prompt": prompt,
        "line_refs": line_refs,
    }

    raw = json.dumps(
        data,
        sort_keys=True,
    )

    return (
        "sha1:"
        + hashlib.sha1(
            raw.encode("utf-8")
        ).hexdigest()
    )


def _make_question(
    question_type: str,
    prompt: str,
    line_refs: list[int],
    answer_format: str,
    answer_key: str | None,
    explanation: str | None = None,
    options: list[str] | None = None,
) -> QuestionPrivate:

    question_hash = _question_hash(
        question_type,
        prompt,
        line_refs,
    )

    return QuestionPrivate(
        id=question_hash,
        type=question_type,
        prompt=prompt,
        line_refs=line_refs,
        answer_format=answer_format,
        options=options,
        max_score=10,
        answer_key=answer_key,
        explanation=explanation,
        question_hash=question_hash,
    )


def _trace_output_question(
    code: str,
    facts: CodeFacts,
) -> QuestionPrivate | None:

    if not facts.functions:
        return None

    function = facts.functions[0]

    # Only attempt simple functions initially.
    args: list[Any] = []

    result = run_code(
        code=code,
        language=facts.language,
        function=function.name,
        args=args,
        timeout=3.0,
    )

    if result.timed_out:
        return None

    if result.exception:
        return None

    output = result.stdout.strip()

    if not output:
        return None

    line_refs = [
        function.start_line,
        function.end_line,
    ]

    prompt = (
        f"What output is produced when the "
        f"function `{function.name}` is executed "
        f"with its default/simple inputs?"
    )

    return _make_question(
        question_type="trace_output",
        prompt=prompt,
        line_refs=line_refs,
        answer_format="short_text",
        answer_key=output,
        explanation=(
            "The answer was obtained by executing "
            "the submitted code."
        ),
    )


def _trace_variable_question(
    code: str,
    facts: CodeFacts,
) -> QuestionPrivate | None:

    if not facts.functions:
        return None

    function = facts.functions[0]

    if not function.params:
        args = []
    else:
        # We currently avoid guessing complicated arguments.
        # A later version will use edge_case_inputs.
        return None

    try:
        trace = trace_run(
            code=code,
            function=function.name,
            args=args,
            max_steps=5000,
        )
    except Exception:
        return None

    if not trace:
        return None

    interesting = None

    for step in trace:

        if step.locals:

            interesting = step
            break

    if interesting is None:
        return None

    variable_names = [
        name
        for name in interesting.locals
        if name != "self"
    ]

    if not variable_names:
        return None

    variable = variable_names[-1]

    answer = str(
        interesting.locals[variable]
    )

    prompt = (
        f"During execution of `{function.name}`, "
        f"what is the value of `{variable}` at "
        f"line {interesting.line}?"
    )

    return _make_question(
        question_type="trace_variable",
        prompt=prompt,
        line_refs=[interesting.line],
        answer_format="short_text",
        answer_key=answer,
        explanation=(
            "The value was captured by the "
            "execution tracer."
        ),
    )


def _edge_case_question(
    code: str,
    facts: CodeFacts,
) -> QuestionPrivate | None:

    if not facts.edge_case_inputs:
        return None

    edge = facts.edge_case_inputs[0]

    result = run_code(
        code=code,
        language=facts.language,
        function=edge.function,
        args=edge.args,
        timeout=3.0,
    )

    if result.timed_out:
        answer = "Execution timed out."

    elif result.exception:
        answer = result.exception

    elif result.return_value is not None:
        answer = result.return_value

    elif result.stdout.strip():
        answer = result.stdout.strip()

    else:
        return None

    function = next(
        (
            f
            for f in facts.functions
            if f.name == edge.function
        ),
        None,
    )

    line_refs = []

    if function:
        line_refs = [
            function.start_line,
            function.end_line,
        ]

    prompt = (
        f"What happens when `{edge.function}` "
        f"is called with the {edge.label} edge case?"
    )

    return _make_question(
        question_type="edge_case",
        prompt=prompt,
        line_refs=line_refs,
        answer_format="short_text",
        answer_key=answer,
        explanation=(
            "The result was obtained by executing "
            "the function with the generated edge case."
        ),
    )



def build_deterministic_questions(
    code: str,
    facts: CodeFacts,
    n: int,
    seed: int,
    *,
    allow_in_process_trace: bool = True,
) -> list[QuestionPrivate]:
    if n <= 0:
        return []

    candidates = [
        _trace_output_question(code, facts),
        (
            _trace_variable_question(code, facts)
            if allow_in_process_trace
            else None
        ),
        _edge_case_question(code, facts),
    ]

    available = [
        question
        for question in candidates
        if question is not None
    ]

    unique: list[QuestionPrivate] = []
    seen: set[str] = set()

    for question in available:
        if question.question_hash not in seen:
            seen.add(question.question_hash)
            unique.append(question)

    # Stable selection for the same code, facts, n, and seed.
    random.Random(seed).shuffle(unique)

    return unique[:n]
