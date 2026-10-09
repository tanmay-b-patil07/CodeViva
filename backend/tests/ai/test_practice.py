"""Tests for CodeViva's practice generator."""

import asyncio

import pytest

from ai.practice import (
    _code_with_line_numbers,
    stream_practice_questions,
)


def test_code_is_numbered_without_changing_line_order():
    code = "def add(a, b):\n    return a + b"

    assert _code_with_line_numbers(code) == (
        "1: def add(a, b):\n"
        "2:     return a + b"
    )


def test_empty_code_is_rejected():
    async def run():
        with pytest.raises(ValueError, match="code cannot be empty"):
            async for _ in stream_practice_questions("", {}):
                pass

    asyncio.run(run())


def test_zero_question_count_is_rejected():
    async def run():
        with pytest.raises(
            ValueError, match="total_questions must be at least 1"
        ):
            async for _ in stream_practice_questions(
                "print('hello')", {}, total_questions=0
            ):
                pass

    asyncio.run(run())