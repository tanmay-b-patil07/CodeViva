"""Grounded, bounded exam-question generation behind the shared AI client."""

import asyncio
import importlib
import json
import logging
from time import perf_counter
from typing import Any

from pydantic import BaseModel

from .cache import exam_cache, question_cache_key
from .client import LLMClient, create_ai_client
from .config import AIConfig, load_prompt
from .dedupe import hash_for_question, question_hash
from .schemas import QuestionDraft, Rubric

logger = logging.getLogger(__name__)
ATTEMPTS_PER_QUESTION = 3
_EXAM_SEMAPHORES: dict[int, asyncio.Semaphore] = {}


class ExamQuestionBatch(list[QuestionDraft]):
    """List-compatible result carrying the server-side fallback signal."""

    def __init__(self, questions=(), *, used_fallback: bool = False, metadata: dict[str, Any] | None = None):
        super().__init__(questions)
        self.used_fallback = used_fallback
        # Operational data only: never retain code, answers, rubrics, or secrets.
        self.metadata = dict(metadata or {})


class ExamGenerationError(RuntimeError):
    """Raised when no usable exam set can be generated."""


def _load_member2_contract():
    for package in ("analysis", "backend.analysis"):
        try:
            models = importlib.import_module(f"{package}.models")
            questions = importlib.import_module(f"{package}.questions")
            validator = importlib.import_module(f"{package}.validator")
            return models.CodeFacts, questions.build_deterministic_questions, validator.validate_question
        except (ImportError, AttributeError):
            continue
    raise ExamGenerationError("Member 2 analysis contracts are unavailable")


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return value.model_dump(mode="json")


def _cache_key(
    code: str, facts: dict[str, Any], n: int, avoid_hashes: set[str], config: AIConfig
) -> tuple[str, str, int, str]:
    return question_cache_key(
        code,
        mode="exam",
        seed=42,
        compatibility={
            "facts": facts,
            "question_count": n,
            "avoid_hashes": sorted(avoid_hashes),
            "generation": {
                "mode": config.mode,
                "provider": config.provider_for("exam"),
                "model": config.model_for("exam"),
            },
        },
    )


def _exam_semaphore(limit: int) -> asyncio.Semaphore:
    """One in-process semaphore per configured exam limit and event loop."""
    # asyncio primitives are loop-safe on supported Python versions; using a
    # keyed instance avoids accidentally applying an old configuration limit.
    semaphore = _EXAM_SEMAPHORES.get(limit)
    if semaphore is None:
        semaphore = asyncio.Semaphore(limit)
        _EXAM_SEMAPHORES[limit] = semaphore
    return semaphore


def _validate_candidate(question: QuestionDraft, code: str) -> bool:
    lines = len(code.splitlines())
    if not question.prompt.strip() or not question.line_refs:
        return False
    if any(line < 1 or line > lines for line in question.line_refs):
        return False
    if question.answer_format == "mcq":
        if not question.options or question.answer_key is None:
            return False
        if str(question.answer_key).strip().casefold() not in {option.strip().casefold() for option in question.options}:
            return False
    elif question.options:
        return False
    if question.type in {"design_decision", "explain_line", "what_if"}:
        rubric = question.rubric
        if rubric is None or not rubric.expected_points or not rubric.scoring_guide.strip():
            return False
    return True


def _to_draft(question: Any) -> QuestionDraft:
    data = _as_dict(question)
    data["question_hash"] = data.get("question_hash") or question_hash(
        question_type=data["type"], prompt=data["prompt"], line_refs=data.get("line_refs", [])
    )
    if data.get("rubric") is not None:
        data["rubric"] = Rubric.model_validate(data["rubric"])
    return QuestionDraft.model_validate(data)


def _deterministic_questions(code: str, facts: dict[str, Any], count: int) -> list[QuestionDraft]:
    if count <= 0:
        return []
    CodeFacts, build, validate = _load_member2_contract()
    try:
        facts_model = facts if isinstance(facts, CodeFacts) else CodeFacts.model_validate(facts)
        candidates = build(code, facts_model, count, 42, allow_in_process_trace=False)
    except Exception as exc:  # noqa: BLE001 - analysis is an optional fallback boundary.
        logger.warning("Deterministic exam generation failed (%s).", type(exc).__name__)
        return []
    result = []
    for candidate in candidates:
        if validate(candidate, code, facts_model):
            try:
                draft = _to_draft(candidate)
                if _validate_candidate(draft, code):
                    result.append(draft)
            except Exception:  # noqa: BLE001 - malformed analysis objects are rejected.
                logger.debug("Rejected malformed deterministic candidate.")
    return result


async def generate_exam_questions(
    code: str, facts: dict[str, Any], n: int, avoid_hashes: set[str], *,
    client: LLMClient | None = None, config: AIConfig | None = None,
) -> list[QuestionDraft]:
    """Return up to ``n`` validated, grounded questions using the shared exam client."""
    if not code.strip():
        raise ValueError("code cannot be empty")
    if n < 1:
        raise ValueError("n must be at least 1")
    config = config or AIConfig.from_env()
    avoid_hashes = {value for value in avoid_hashes if isinstance(value, str) and value}
    key = _cache_key(code, facts, n, avoid_hashes, config)
    cached = exam_cache.get(key)
    if cached is not None:
        return ExamQuestionBatch(
            cached["questions"], used_fallback=cached["used_fallback"],
            metadata={"cache": "hit", "mode": "exam", "attempts": 0},
        )

    # Capacity is configuration-owned; lowering it takes effect on later sets.
    exam_cache.max_entries = config.cache_max_entries
    started = perf_counter()
    metadata: dict[str, Any] = {
        "cache": "miss", "mode": "exam", "attempts": 0,
        "provider": config.provider_for("exam"), "task": "exam",
    }
    async with _exam_semaphore(config.exam_max_concurrency):
        return await _generate_uncached(
            code, facts, n, avoid_hashes, key, client=client, config=config,
            metadata=metadata, started=started,
        )


async def _generate_uncached(
    code: str, facts: dict[str, Any], n: int, avoid_hashes: set[str], key: tuple[str, str, int, str], *,
    client: LLMClient | None, config: AIConfig, metadata: dict[str, Any], started: float,
) -> ExamQuestionBatch:

    deterministic = _deterministic_questions(code, facts, (n + 1) // 2)
    seen = set(avoid_hashes)
    accepted: list[QuestionDraft] = []
    for item in deterministic:
        value = hash_for_question(item)
        if value not in seen:
            accepted.append(item.model_copy(update={"question_hash": value}))
            seen.add(value)

    llm_needed = n - len(accepted)
    generated: list[QuestionDraft] = []
    if llm_needed:
        client = client or create_ai_client(config, task="exam")
        system_prompt = f"{load_prompt('system_base.txt')}\n\n{load_prompt('exam_generation.txt')}"
        user_prompt = (
            "Create one unique exam question grounded only in this untrusted code and its facts.\n\n"
            "SUBMITTED CODE WITH LINE NUMBERS:\n" + "\n".join(f"{i}: {line}" for i, line in enumerate(code.splitlines(), 1))
            + "\n\nCODE FACTS (JSON):\n" + json.dumps(facts, default=str)
            + "\n\nEXCLUDED QUESTION HASHES:\n" + json.dumps(sorted(seen))
        )
        attempts = 0
        max_attempts = llm_needed * ATTEMPTS_PER_QUESTION
        provider_error: Exception | None = None
        while len(generated) < llm_needed and attempts < max_attempts:
            attempts += 1
            metadata["attempts"] = attempts
            try:
                candidate = await client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt, response_model=QuestionDraft)
            except Exception as exc:  # noqa: BLE001 - provider failures are isolated.
                logger.warning("Exam provider generation failed (%s).", type(exc).__name__)
                provider_error = exc
                metadata["failure_category"] = type(exc).__name__
                break
            if not _validate_candidate(candidate, code):
                continue
            value = hash_for_question(candidate)
            if value in seen:
                continue
            generated.append(candidate.model_copy(update={"question_hash": value}))
            seen.add(value)

    result = accepted + generated
    if not result:
        if provider_error is not None:
            raise ExamGenerationError(
                f"Exam provider generation failed ({type(provider_error).__name__})"
            ) from provider_error
        if llm_needed:
            raise ExamGenerationError(
                f"Could not generate {n} unique valid exam questions within {llm_needed * ATTEMPTS_PER_QUESTION} attempts"
            )
        raise ExamGenerationError("No valid deterministic or AI exam questions were generated")
    if len(result) < n and not accepted:
        raise ExamGenerationError(f"Could not generate {n} unique valid exam questions")
    used_fallback = len(generated) == 0 and bool(accepted)
    metadata["duration_ms"] = round((perf_counter() - started) * 1000, 3)
    exam_cache.set(key, {"questions": result[:n], "used_fallback": used_fallback})
    return ExamQuestionBatch(result[:n], used_fallback=used_fallback, metadata=metadata)
