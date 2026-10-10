"""Provider-neutral AI clients, including offline and OpenAI-compatible modes."""

import asyncio
import json
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .config import AIConfig, load_prompt
from .schemas import JudgeOutput, QuestionDraft

T = TypeVar("T", bound=BaseModel)


class AIClientError(RuntimeError):
    """Base error for secret-safe AI client failures."""


class ProviderNotConfiguredError(AIClientError):
    pass


class ProviderRequestError(AIClientError):
    pass


class InvalidAIResponseError(AIClientError):
    pass


class LLMClient(Protocol):
    async def generate_json(
        self, *, system_prompt: str, user_prompt: str, response_model: type[T]
    ) -> T: ...


class MockLLMClient:
    """Offline client returning schema-validated sample responses."""

    async def generate_json(
        self, *, system_prompt: str, user_prompt: str, response_model: type[T]
    ) -> T:
        if not system_prompt.strip():
            raise ValueError("system_prompt cannot be empty")
        if not user_prompt.strip():
            raise ValueError("user_prompt cannot be empty")
        if response_model is QuestionDraft:
            prompt = system_prompt.casefold()
            if "complexity" in prompt:
                data: dict[str, Any] = {
                    "type": "complexity",
                    "prompt": "What is the time complexity of this algorithm?",
                    "line_refs": [1],
                    "answer_format": "mcq",
                    "options": ["O(1)", "O(n)", "O(n²)"],
                    "max_score": 10,
                    "answer_key": "O(n)",
                    "rubric": None,
                    "explanation": "Illustrative mock answer only. This is not inferred from the submitted code.",
                    "question_hash": "mock-complexity-question",
                }
            elif (
                "counterfactual" in prompt or "what_if" in prompt or "what if" in prompt
            ):
                data = {
                    "type": "what_if",
                    "prompt": "What could change if the condition were reversed?",
                    "line_refs": [1],
                    "answer_format": "free_text",
                    "options": None,
                    "max_score": 10,
                    "answer_key": None,
                    "rubric": {
                        "expected_points": [
                            "Explains a plausible effect of the change"
                        ],
                        "common_misconceptions": [],
                        "scoring_guide": "Illustrative mock rubric only.",
                    },
                    "explanation": "Mock explanation only; verify the actual code before using an answer.",
                    "question_hash": "mock-what-if-question",
                }
            elif "explain" in prompt:
                data = {
                    "type": "explain_line",
                    "prompt": "Explain the purpose of the selected statement.",
                    "line_refs": [1],
                    "answer_format": "free_text",
                    "options": None,
                    "max_score": 10,
                    "answer_key": None,
                    "rubric": {
                        "expected_points": ["Describes the statement's purpose"],
                        "common_misconceptions": [],
                        "scoring_guide": "Illustrative mock rubric only.",
                    },
                    "explanation": "Mock explanation of what a useful answer should cover.",
                    "question_hash": "mock-explain-question",
                }
            else:
                data = {
                    "type": "design_decision",
                    "prompt": "Why is this data structure suitable for the operation?",
                    "line_refs": [1],
                    "answer_format": "free_text",
                    "options": None,
                    "max_score": 10,
                    "answer_key": None,
                    "rubric": {
                        "expected_points": [
                            "Explains the data structure's role in the code"
                        ],
                        "common_misconceptions": [],
                        "scoring_guide": "Award credit for a relevant explanation.",
                    },
                    "explanation": "Mock explanation for offline testing.",
                    "question_hash": "mock-design-question",
                }
        elif response_model is JudgeOutput:
            data = {
                "score": 8,
                "evidence": "Mock evidence from the sample answer.",
                "confidence": 0.85,
                "feedback": "Mock feedback: the main idea is understood.",
            }
        else:
            raise InvalidAIResponseError(
                f"No mock response configured for {response_model.__name__}"
            )
        try:
            return response_model.model_validate(data)
        except Exception as exc:
            raise InvalidAIResponseError(
                f"Mock response failed validation for {response_model.__name__}"
            ) from exc


def chat_completions_url(base_url: str) -> str:
    """Canonicalise a configured OpenAI-compatible endpoint exactly once."""
    base = base_url.strip().rstrip("/")
    if not base:
        raise ProviderNotConfiguredError("Provider base URL is required in live mode")
    if base.endswith("/chat/completions"):
        return base
    return (
        f"{base}/chat/completions"
        if base.endswith("/v1")
        else f"{base}/v1/chat/completions"
    )


class OpenAICompatibleClient:
    """Minimal adapter for xAI and Agnes chat-completions APIs."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 20,
        max_retries: int = 1,
        max_concurrency: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider, self.endpoint, self.model, self.max_retries = (
            provider,
            chat_completions_url(base_url),
            model,
            max_retries,
        )
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            limits=httpx.Limits(max_connections=max_concurrency),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def generate_json(
        self, *, system_prompt: str, user_prompt: str, response_model: type[T]
    ) -> T:
        if not system_prompt.strip() or not user_prompt.strip():
            raise ValueError("system_prompt and user_prompt cannot be empty")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\n\nReturn one valid JSON object only.",
                },
                {"role": "user", "content": user_prompt},
            ],
        }
        response = await self._request(payload)
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InvalidAIResponseError(
                "Provider response did not contain chat completion content"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise InvalidAIResponseError("Provider response content was empty")

        # Extract JSON from markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            # Remove markdown code block wrapper
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()

        try:
            return response_model.model_validate(json.loads(content))
        except json.JSONDecodeError as exc:
            raise InvalidAIResponseError(
                "Provider response was not valid JSON"
            ) from exc
        except ValidationError as exc:
            raise InvalidAIResponseError(
                f"Provider response did not match {response_model.__name__}"
            ) from exc

    async def _request(self, payload: dict[str, Any]) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    self.endpoint, headers=self._headers, json=payload
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self.max_retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise ProviderRequestError(
                    "Provider connection or timeout failure"
                ) from exc
            if response.status_code in {408, 429} or response.status_code >= 500:
                if attempt < self.max_retries:
                    await asyncio.sleep(0.05 * (2**attempt))
                    continue
                raise ProviderRequestError(
                    f"{self.provider} provider request failed after retries (HTTP {response.status_code})"
                )
            if response.status_code >= 400:
                raise ProviderRequestError(
                    f"{self.provider} provider rejected the request (HTTP {response.status_code})"
                )
            return response
        raise AssertionError("unreachable")


def create_ai_client(
    config: AIConfig | None = None,
    *,
    task: str = "practice",
    transport: httpx.AsyncBaseTransport | None = None,
) -> LLMClient:
    """Create a task-routed client; mock mode never opens a network connection."""
    config = config or AIConfig.from_env()
    if config.mode == "mock":
        if config.provider != "mock":
            raise ProviderNotConfiguredError(
                "CODEVIVA_AI_PROVIDER is legacy; use CODEVIVA_AI_MODE=live and task routing variables"
            )
        return MockLLMClient()
    provider, credential, model = (
        config.provider_for(task),
        None,
        config.model_for(task),
    )
    credential = config.credential_for(provider)
    if not credential:
        raise ProviderNotConfiguredError(
            f"{provider} requires its API key in live mode"
        )
    if not model:
        raise ProviderNotConfiguredError(
            f"{provider} requires a model for {task} in live mode"
        )
    return OpenAICompatibleClient(
        provider=provider,
        base_url=config.base_url_for(provider),
        api_key=credential,
        model=model,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        max_concurrency=config.max_concurrency,
        transport=transport,
    )


__all__ = [
    "AIClientError",
    "InvalidAIResponseError",
    "LLMClient",
    "MockLLMClient",
    "OpenAICompatibleClient",
    "ProviderNotConfiguredError",
    "ProviderRequestError",
    "chat_completions_url",
    "create_ai_client",
    "load_prompt",
]
