from __future__ import annotations

from .languages import get_adapter
from .models import CodeFacts


def extract_facts(
    code: str,
    language: str = "python",
) -> CodeFacts:

    adapter = get_adapter(language)

    return adapter.analyze(code)