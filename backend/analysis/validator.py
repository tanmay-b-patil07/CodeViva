from __future__ import annotations

import hashlib
import json

from .models import CodeFacts, QuestionPrivate


def validate_question(
    q: QuestionPrivate,
    code: str,
    facts: CodeFacts,
) -> list[str]:
    """
    Validate a generated question against the submitted code
    and the shared CodeViva contracts.

    Returns:
        []      -> question is valid
        [errors] -> question has one or more problems
    """

    problems: list[str] = []

    # ---------------------------------------------------------
    # 1. Prompt must not be empty
    # ---------------------------------------------------------

    if not q.prompt.strip():
        problems.append("Question prompt is empty.")

    # ---------------------------------------------------------
    # 2. Line references must exist
    # ---------------------------------------------------------

    for line in q.line_refs:

        if line < 1:
            problems.append(
                f"Invalid line reference: {line}."
            )

        elif line > facts.line_count:
            problems.append(
                f"Line reference {line} is outside "
                f"the code ({facts.line_count} lines)."
            )

    # ---------------------------------------------------------
    # 3. Deterministic questions need answer keys
    # ---------------------------------------------------------

    deterministic_types = {
        "trace_output",
        "trace_variable",
        "edge_case",
        "complexity",
    }

    if q.type in deterministic_types:

        if (
            q.answer_key is None
            or not str(q.answer_key).strip()
        ):
            problems.append(
                "Deterministic question has no answer key."
            )

    # ---------------------------------------------------------
    # 4. MCQ validation
    # ---------------------------------------------------------

    if q.answer_format == "mcq":

        if not q.options:
            problems.append(
                "MCQ question has no options."
            )

        else:

            # Remove whitespace around options.
            options = [
                option.strip()
                for option in q.options
            ]

            # Need between 3 and 5 options.
            if not 3 <= len(options) <= 5:
                problems.append(
                    "MCQ must contain between "
                    "3 and 5 options."
                )

            # Options must be distinct.
            normalized = [
                option.casefold()
                for option in options
            ]

            if len(normalized) != len(set(normalized)):
                problems.append(
                    "MCQ contains duplicate options."
                )

            # Answer must be one of the options.
            if q.answer_key is not None:

                answer = str(
                    q.answer_key
                ).strip().casefold()

                if answer not in normalized:
                    problems.append(
                        "MCQ answer key does not match "
                        "any option."
                    )

    # ---------------------------------------------------------
    # 5. Non-MCQ questions should not require options
    # ---------------------------------------------------------

    elif q.options:

        problems.append(
            "Non-MCQ question should not contain options."
        )

    # ---------------------------------------------------------
    # 6. Question hash validation
    # ---------------------------------------------------------

    expected_hash = _calculate_question_hash(q)

    if q.question_hash != expected_hash:
        problems.append(
            "Question hash does not match question content."
        )

    # ---------------------------------------------------------
    # 7. Question type validation
    # ---------------------------------------------------------

    allowed_types = {
        "trace_output",
        "trace_variable",
        "edge_case",
        "complexity",
        "design_decision",
        "explain_line",
        "what_if",
    }

    if q.type not in allowed_types:
        problems.append(
            f"Unsupported question type: {q.type}"
        )

    # ---------------------------------------------------------
    # 8. Answer format validation
    # ---------------------------------------------------------

    allowed_formats = {
        "mcq",
        "numeric",
        "short_text",
        "free_text",
    }

    if q.answer_format not in allowed_formats:
        problems.append(
            f"Unsupported answer format: "
            f"{q.answer_format}"
        )

    # ---------------------------------------------------------
    # 9. Code must not be empty
    # ---------------------------------------------------------

    if not code.strip():
        problems.append(
            "Submitted code is empty."
        )

    return problems


def _calculate_question_hash(
    q: QuestionPrivate,
) -> str:

    data = {
        "type": q.type,
        "prompt": q.prompt,
        "line_refs": q.line_refs,
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