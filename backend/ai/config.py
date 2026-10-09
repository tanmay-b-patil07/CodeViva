"""Configuration for CodeViva's AI layer.

Live requests are opt-in through ``CODEVIVA_AI_MODE=live``. The default stays
offline mock mode even when provider credentials are present.
"""

import os
from dataclasses import dataclass
from pathlib import Path

AI_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = AI_DIR / "prompts"
_TASKS = {"practice", "exam", "grading"}
_PROVIDERS = {"agnes", "grok"}


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _provider(value: str, setting: str) -> str:
    normalized = value.strip().lower()
    if normalized == "xai":
        normalized = "grok"
    if normalized not in _PROVIDERS:
        raise ValueError(f"{setting} must be one of: agnes, grok")
    return normalized


@dataclass(frozen=True)
class AIConfig:
    """Runtime settings. Secrets are read from the environment only."""

    # Retained for source compatibility with the original mock-only client.
    provider: str = "mock"
    model_practice: str | None = None
    model_exam: str | None = None
    model_grading: str | None = None
    api_key: str | None = None
    timeout_seconds: float = 20.0
    max_retries: int = 1
    max_concurrency: int = 3
    exam_max_concurrency: int = 3
    cache_max_entries: int = 128
    review_confidence_threshold: float = 0.6
    mode: str = "mock"
    provider_practice: str = "agnes"
    provider_exam: str = "grok"
    provider_grading: str = "grok"
    xai_api_key: str | None = None
    agnes_api_key: str | None = None
    xai_base_url: str = "https://api.x.ai/v1"
    agnes_base_url: str = "https://apihub.agnes-ai.com/v1"
    xai_model: str | None = None
    agnes_model: str | None = None

    @classmethod
    def from_env(cls) -> "AIConfig":
        """Read settings without printing/logging credentials.

        The selected provider's explicit model (AGNES_MODEL or XAI_MODEL) wins.
        Legacy task variables are only fallbacks: CODEVIVA_MODEL_<TASK> then
        MODEL_<TASK>. This prevents a legacy Anthropic model from
        being sent to an Agnes or xAI request when a provider model is set.
        """
        timeout = float(os.getenv("CODEVIVA_AI_TIMEOUT", "20"))
        retries = int(os.getenv("CODEVIVA_AI_MAX_RETRIES", "1"))
        concurrency = int(os.getenv("CODEVIVA_AI_MAX_CONCURRENCY", "3"))
        exam_concurrency = int(os.getenv("CODEVIVA_AI_EXAM_MAX_CONCURRENCY", "3"))
        cache_max_entries = int(os.getenv("CODEVIVA_AI_CACHE_MAX_ENTRIES", "128"))
        threshold = float(os.getenv("CODEVIVA_AI_REVIEW_THRESHOLD", "0.6"))
        mode = os.getenv("CODEVIVA_AI_MODE", "mock").strip().lower()
        if mode not in {"mock", "live"}:
            raise ValueError("CODEVIVA_AI_MODE must be mock or live")
        if timeout <= 0:
            raise ValueError("CODEVIVA_AI_TIMEOUT must be greater than zero")
        if retries < 0:
            raise ValueError("CODEVIVA_AI_MAX_RETRIES cannot be negative")
        if not 1 <= concurrency <= 5:
            raise ValueError("CODEVIVA_AI_MAX_CONCURRENCY must be between 1 and 5")
        if not 1 <= exam_concurrency <= 5:
            raise ValueError("CODEVIVA_AI_EXAM_MAX_CONCURRENCY must be between 1 and 5")
        if cache_max_entries < 1:
            raise ValueError("CODEVIVA_AI_CACHE_MAX_ENTRIES must be at least 1")
        if not 0 <= threshold <= 1:
            raise ValueError("CODEVIVA_AI_REVIEW_THRESHOLD must be between 0 and 1")
        return cls(
            provider=os.getenv("CODEVIVA_AI_PROVIDER", "mock").strip().lower(),
            model_practice=_optional_env("CODEVIVA_MODEL_PRACTICE")
            or _optional_env("MODEL_PRACTICE"),
            model_exam=_optional_env("CODEVIVA_MODEL_EXAM")
            or _optional_env("MODEL_EXAM"),
            model_grading=_optional_env("CODEVIVA_MODEL_GRADING")
            or _optional_env("MODEL_GRADING"),
            api_key=_optional_env("CODEVIVA_AI_API_KEY"),
            timeout_seconds=timeout,
            max_retries=retries,
            max_concurrency=concurrency,
            exam_max_concurrency=exam_concurrency,
            cache_max_entries=cache_max_entries,
            review_confidence_threshold=threshold,
            mode=mode,
            provider_practice=_provider(
                os.getenv("CODEVIVA_AI_PROVIDER_PRACTICE", "agnes"),
                "CODEVIVA_AI_PROVIDER_PRACTICE",
            ),
            provider_exam=_provider(
                os.getenv("CODEVIVA_AI_PROVIDER_EXAM", "grok"),
                "CODEVIVA_AI_PROVIDER_EXAM",
            ),
            provider_grading=_provider(
                os.getenv("CODEVIVA_AI_PROVIDER_GRADING", "grok"),
                "CODEVIVA_AI_PROVIDER_GRADING",
            ),
            xai_api_key=_optional_env("XAI_API_KEY"),
            agnes_api_key=_optional_env("AGNES_API_KEY"),
            xai_base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").strip(),
            agnes_base_url=os.getenv(
                "AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1"
            ).strip(),
            xai_model=_optional_env("XAI_MODEL"),
            agnes_model=_optional_env("AGNES_MODEL"),
        )

    def provider_for(self, task: str) -> str:
        if task not in _TASKS:
            raise ValueError("task must be practice, exam, or grading")
        return getattr(self, f"provider_{task}")

    def credential_for(self, provider: str) -> str | None:
        return self.agnes_api_key if provider == "agnes" else self.xai_api_key

    def base_url_for(self, provider: str) -> str:
        return self.agnes_base_url if provider == "agnes" else self.xai_base_url

    def model_for(self, task: str) -> str | None:
        provider_model = (
            self.agnes_model if self.provider_for(task) == "agnes" else self.xai_model
        )
        if provider_model:
            return provider_model
        if task == "practice" and self.model_practice:
            return self.model_practice
        if task == "exam" and self.model_exam:
            return self.model_exam
        if task == "grading" and self.model_grading:
            return self.model_grading
        return None


def load_prompt(name: str) -> str:
    """Load a named prompt from backend/ai/prompts."""
    if not name or Path(name).name != name:
        raise ValueError("Prompt name must be a filename, not a path")
    path = PROMPTS_DIR / name
    if path.suffix != ".txt":
        raise ValueError("Prompt files must use the .txt extension")
    return path.read_text(encoding="utf-8")
