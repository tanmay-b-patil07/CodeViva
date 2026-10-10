from __future__ import annotations

from .base import LanguageAdapter


_ADAPTERS: dict[str, LanguageAdapter] = {}


def register_adapter(adapter: LanguageAdapter) -> None:
    """
    Register a language adapter.
    """
    _ADAPTERS[adapter.name.lower()] = adapter


def get_adapter(language: str) -> LanguageAdapter:
    """
    Get the adapter for a language.
    """
    key = language.strip().lower()

    if key not in _ADAPTERS:
        supported = ", ".join(sorted(_ADAPTERS))
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Supported languages: {supported}"
        )

    return _ADAPTERS[key]


def supported_languages() -> list[str]:
    return sorted(_ADAPTERS.keys())
