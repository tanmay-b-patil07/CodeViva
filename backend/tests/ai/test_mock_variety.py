
import asyncio

from backend.ai.client import MockLLMClient
from backend.ai.schemas import QuestionDraft


def test_mock_client_returns_varied_question_types():
    client = MockLLMClient()

    tasks = [
        "TASK: Create one question about a design decision.",
        "TASK: Create one question asking the student to explain a specific line.",
        "TASK: Create one question about the time or space complexity.",
        "TASK: Create one counterfactual question.",
    ]

    async def run():
        results = []
        for task in tasks:
            result = await client.generate_json(
                system_prompt=task,
                user_prompt="Test code context.",
                response_model=QuestionDraft,
            )
            results.append(result)
        return results

    questions = asyncio.run(run())

    assert [q.type for q in questions] == [
        "design_decision",
        "explain_line",
        "complexity",
        "what_if",
    ]
    assert len({q.question_hash for q in questions}) == 4
    assert all(q.prompt.strip() for q in questions)


def test_mock_complexity_question_has_distinct_options():
    async def run():
        return await MockLLMClient().generate_json(
            system_prompt="TASK: Create one question about the time or space complexity.",
            user_prompt="Test code context.",
            response_model=QuestionDraft,
        )

    question = asyncio.run(run())

    assert question.answer_format == "mcq"
    assert question.options is not None
    assert 3 <= len(question.options) <= 5
    assert len(set(question.options)) == len(question.options)
