
"""Practice question generation for CodeViva."""

import importlib
import json
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from .client import LLMClient, create_ai_client, load_prompt
from .config import AIConfig
from .dedupe import hash_for_question, question_hash
from .schemas import QuestionDraft

logger = logging.getLogger(__name__)

PRACTICE_QUESTION_COUNT = 5
DETERMINISTIC_QUESTION_COUNT = 3
MAX_LLM_ATTEMPTS = 8


class PracticeGenerationError(RuntimeError):
    """Raised when required practice-generation dependencies are unavailable."""


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Unsupported model type: {type(value).__name__}")


def _load_member2_contract():
    """Import Member 2's models, question builder, and validator."""
    failures: list[Exception] = []

    for package in ("analysis", "backend.analysis"):
        try:
            models = importlib.import_module(f"{package}.models")
            questions = importlib.import_module(f"{package}.questions")
            validator = importlib.import_module(f"{package}.validator")

            return (
                getattr(models, "CodeFacts"),
                getattr(models, "QuestionPrivate"),
                getattr(questions, "build_deterministic_questions"),
                getattr(validator, "validate_question"),
            )
        except (ImportError, AttributeError) as exc:
            failures.append(exc)

    raise PracticeGenerationError(
        "Member 2's models, deterministic question builder, or validator "
        "are unavailable. Restore these modules before integration testing."
    ) from failures[-1]


def _normalise_facts(
    facts: Any,
    code_facts_model: type,
) -> tuple[Any, dict[str, Any]]:
    """Convert stored facts to Member 2's model and JSON-compatible data."""
    if isinstance(facts, code_facts_model):
        model = facts
    else:
        try:
            model = code_facts_model.model_validate(facts)
        except Exception as exc:
            raise PracticeGenerationError(
                "The supplied facts do not match Member 2's CodeFacts schema."
            ) from exc

    return model, _as_dict(model)


def _code_with_line_numbers(code: str) -> str:
    return "\n".join(
        f"{number}: {line}"
        for number, line in enumerate(code.splitlines(), start=1)
    )


def _question_hash(question: QuestionDraft) -> str:
    """Return the Member 2 validator's content hash for a private question."""
    return question_hash(
        question_type=question.type, prompt=question.prompt, line_refs=question.line_refs
    )


def _to_private_question(
    draft: QuestionDraft,
    private_model: type,
) -> Any:
    """Convert a validated AI draft to Member 2's private question model."""
    data = draft.model_dump()
    if isinstance(data["answer_key"], dict):
        raise PracticeGenerationError(
            "Dictionary answer keys are not supported by Member 2 practice "
            "questions."
        )
    data["id"] = str(uuid4())
    # Provider-provided labels are not a persistence identity; use Member 2's
    # content hash consistently even when a provider includes another value.
    data["question_hash"] = _question_hash(draft)

    try:
        return private_model.model_validate(data)
    except Exception as exc:
        raise PracticeGenerationError(
            "The generated draft does not match Member 2's QuestionPrivate schema."
        ) from exc


async def stream_practice_questions(
    code: str,
    facts: Any,
    *,
    client: LLMClient | None = None,
    config: AIConfig | None = None,
    total_questions: int = PRACTICE_QUESTION_COUNT,
    seed: int = 42,
    avoid_hashes: set[str] | None = None,
) -> AsyncIterator[Any]:
    """Yield validated deterministic questions before valid AI questions.

    Existing question hashes can be supplied when resuming a session.
    Answer keys and explanations are included for practice mode only.
    """
    if not code.strip():
        raise ValueError("code cannot be empty")
    if total_questions < 1:
        raise ValueError("total_questions must be at least 1")

    config = config or AIConfig.from_env()

    (
        code_facts_model,
        private_question_model,
        build_questions,
        validate_question,
    ) = _load_member2_contract()

    facts_model, facts_data = _normalise_facts(facts, code_facts_model)

    seen_hashes = set(avoid_hashes or ())
    client = client or create_ai_client(config, task="practice")
    yielded = 0

    deterministic = build_questions(
        code,
        facts_model,
        min(DETERMINISTIC_QUESTION_COUNT, total_questions),
        seed,
        allow_in_process_trace=False,
    )

    # Deterministic execution-derived questions always come first.
    for question in deterministic:
        problems = validate_question(question, code, facts_model)
        if problems:
            logger.debug(
                "Skipping invalid deterministic question: %s", problems
            )
            continue

        content_hash = hash_for_question(question)
        if content_hash in seen_hashes:
            continue

        seen_hashes.add(content_hash)
        yield question
        yielded += 1

        if yielded >= total_questions:
            return

    system_base = load_prompt("system_base.txt")
    user_prompt = (
        "Create one code-specific practice question.\n\n"
        "SUBMITTED CODE WITH LINE NUMBERS:\n"
        f"{_code_with_line_numbers(code)}\n\n"
        "CODE FACTS (JSON):\n"
        f"{json.dumps(facts_data, ensure_ascii=False, default=str)}\n\n"
        "Ground the question in this code. Do not invent execution results."
    )

    prompt_names = [
        "design_decision.txt",
        "explain_line.txt",
        "complexity.txt",
        "what_if.txt",
    ]

    attempts = 0

    while yielded < total_questions and attempts < MAX_LLM_ATTEMPTS:
        task_prompt = load_prompt(prompt_names[attempts % len(prompt_names)])
        attempts += 1

        try:
            draft = await client.generate_json(
                system_prompt=f"{system_base}\n\n{task_prompt}",
                user_prompt=user_prompt,
                response_model=QuestionDraft,
            )
        except Exception as exc:
            logger.warning(
                "Practice candidate generation failed (%s).",
                type(exc).__name__,
            )
            continue

        # Trace and edge-case answer keys must come from real execution.
        if draft.type in {"trace_output", "trace_variable", "edge_case"}:
            logger.debug("Skipping LLM-proposed deterministic question type.")
            continue

        line_count = len(code.splitlines())
        if not draft.line_refs or any(
            line < 1 or line > line_count for line in draft.line_refs
        ):
            logger.debug("Skipping candidate with invalid line references.")
            continue

        if draft.answer_format == "mcq" and not draft.options:
            logger.debug("Skipping MCQ candidate without options.")
            continue

        try:
            question = _to_private_question(
                draft,
                private_question_model,
            )
        except PracticeGenerationError as exc:
            logger.debug("Skipping invalid question draft: %s", exc)
            continue

        problems = validate_question(question, code, facts_model)
        if problems:
            logger.debug("Skipping invalid LLM question: %s", problems)
            continue

        data = _as_dict(question)
        content_hash = hash_for_question(question)

        if content_hash in seen_hashes:
            logger.debug("Skipping duplicate practice question.")
            continue

        seen_hashes.add(content_hash)
        yield question
        yielded += 1

    if yielded == 0:
        raise PracticeGenerationError(
            "No valid practice questions were generated. "
            "Check the code, CodeFacts, and Member 2 validator."
        )
