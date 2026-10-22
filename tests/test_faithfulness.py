from unittest.mock import AsyncMock

from app.evaluation.faithfulness import build_judge_prompt, judge_faithfulness


async def test_judge_parses_well_formed_response():
    client = AsyncMock()
    client.chat.return_value = (
        '{"faithfulness": 0.9, "relevance": 1.0, "reasoning": "Answer matches the source."}'
    )
    result = await judge_faithfulness(
        "What's the default?", "It's 3.", ["MAX_RETRY_LIMIT defaults to 3."], client
    )

    assert result.faithfulness == 0.9
    assert result.relevance == 1.0
    assert result.skipped is False


async def test_judge_strips_markdown_fences():
    client = AsyncMock()
    client.chat.return_value = (
        '```json\n{"faithfulness": 0.5, "relevance": 0.5, "reasoning": "partial"}\n```'
    )
    result = await judge_faithfulness("q", "a", ["source text"], client)
    assert result.faithfulness == 0.5


async def test_judge_falls_back_to_zero_not_neutral_on_malformed_response():
    client = AsyncMock()
    client.chat.return_value = "not valid json"
    result = await judge_faithfulness("q", "a", ["source text"], client)

    assert result.faithfulness == 0.0
    assert result.relevance == 0.0


async def test_judge_skips_llm_call_when_no_cited_sources():
    client = AsyncMock()
    result = await judge_faithfulness("q", "I don't have enough info.", [], client)

    assert result.skipped is True
    assert result.faithfulness == 1.0
    client.chat.assert_not_called()


def test_build_judge_prompt_includes_query_answer_and_sources():
    messages = build_judge_prompt("What's X?", "X is Y.", ["source about X and Y"])
    user_content = messages[1]["content"]
    assert "What's X?" in user_content
    assert "X is Y." in user_content
    assert "source about X and Y" in user_content
    assert "[Source 1]" in user_content
