from typing import Any


def extract_facts(code: str) -> dict[str, Any]:
    """
    Integration boundary for Member 2's analysis package.

    Member 1 owns this adapter.
    Member 2 owns the implementation of extract_facts().
    """
    try:
        from analysis import extract_facts as member2_extract_facts
    except ImportError as exc:
        raise RuntimeError(
            "Member 2 analysis package is not available."
        ) from exc

    facts = member2_extract_facts(code)

    if hasattr(facts, "model_dump"):
        return facts.model_dump(mode="json")

    if isinstance(facts, dict):
        return facts

    raise TypeError(
        "Member 2 extract_facts() returned an unsupported result type."
    )