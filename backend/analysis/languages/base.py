from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import CodeFacts, RunResult, TraceStep


class LanguageAdapter(ABC):
    """
    Base interface every supported programming language must implement.
    """

    name: str
    extensions: tuple[str, ...]

    @abstractmethod
    def analyze(self, code: str) -> CodeFacts:
        """
        Analyze source code without executing it.
        """
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        code: str,
        function: str | None,
        args: list[Any],
        timeout: float,
    ) -> RunResult:
        """
        Execute code safely and return normalized results.
        """
        raise NotImplementedError

    def trace(
        self,
        code: str,
        function: str,
        args: list[Any],
        max_steps: int = 5000,
    ) -> list[TraceStep]:
        """
        Optional tracing implementation.

        Languages that don't yet support tracing can return
        an empty list or raise NotImplementedError.
        """
        raise NotImplementedError(
            f"Tracing is not implemented for {self.name}"
        )