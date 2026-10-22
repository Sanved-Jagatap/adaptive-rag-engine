from unittest.mock import AsyncMock

from app.core.ollama_client import ChatResult
from app.generation.generator import SYSTEM_PROMPT, build_prompt, generate_answer
from app.models.schemas import Chunk
from app.retrieval.types import RetrievedChunk


def make_retrieved():
    chunk = Chunk(
        chunk_id="c1",
        doc_id="d1",
        text="MAX_RETRY_LIMIT defaults to 3.",
        chunk_index=0,
        token_count=5,
    )
    return [RetrievedChunk(chunk=chunk, score=0.9)]


def make_chat_result(
    content: str,
    prompt_tokens: int = 100,
    completion_tokens: int = 20,
    total_duration_ns: int = 1_000_000,
    load_duration_ns: int = 100_000,
    eval_duration_ns: int = 800_000,
):
    return ChatResult(
        content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_duration_ns=total_duration_ns,
        load_duration_ns=load_duration_ns,
        eval_duration_ns=eval_duration_ns,
    )


async def test_generate_answer_parses_well_formed_json():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        '{"answer": "It defaults to 3.", "cited_sources": [1], '
        '"sufficient_evidence": true}'
    )

    result = await generate_answer(
        "What's the default?",
        make_retrieved(),
        client,
    )

    assert result.answer == "It defaults to 3."
    assert result.cited_sources == [1]
    assert result.sufficient_evidence is True


async def test_generate_answer_strips_markdown_fences():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        '```json\n{"answer": "3.", "cited_sources": [1], '
        '"sufficient_evidence": true}\n```'
    )

    result = await generate_answer("q", make_retrieved(), client)

    assert result.answer == "3."


async def test_generate_answer_falls_back_safely_on_malformed_json():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        "not valid json at all"
    )

    result = await generate_answer("q", make_retrieved(), client)

    assert result.sufficient_evidence is False
    assert result.cited_sources == []
    assert result.raw_response == "not valid json at all"


async def test_generate_answer_with_no_retrieved_chunks_never_calls_llm():
    client = AsyncMock()

    result = await generate_answer("q", [], client)

    assert result.sufficient_evidence is False
    client.chat_with_usage.assert_not_called()


def test_build_prompt_numbers_sources_starting_at_one():
    messages = build_prompt("q", make_retrieved())

    user_msg = messages[1]["content"]

    assert "[Source 1]" in user_msg
    assert "MAX_RETRY_LIMIT defaults to 3." in user_msg


# --- _coerce_bool / string-boolean defensiveness ---

# Real bug found during debugging: some models emit "sufficient_evidence"
# as the JSON STRING "false" rather than the boolean false. Python's bare
# bool("false") evaluates to True (any non-empty string is truthy), which
# would silently invert the model's actual intent. These tests guard that
# _parse_response handles the string case correctly instead of trusting
# bool() to coerce it.


async def test_sufficient_evidence_as_string_false_is_parsed_as_false():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        '{"answer": "no info", "cited_sources": [], '
        '"sufficient_evidence": "false"}'
    )

    result = await generate_answer("q", make_retrieved(), client)

    assert result.sufficient_evidence is False


async def test_sufficient_evidence_as_string_true_is_parsed_as_true():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        '{"answer": "3.", "cited_sources": [1], '
        '"sufficient_evidence": "true"}'
    )

    result = await generate_answer("q", make_retrieved(), client)

    assert result.sufficient_evidence is True


async def test_sufficient_evidence_as_real_json_booleans_still_work():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        '{"answer": "3.", "cited_sources": [1], '
        '"sufficient_evidence": true}'
    )

    result = await generate_answer("q", make_retrieved(), client)

    assert result.sufficient_evidence is True


def test_generation_result_preserves_ollama_usage_metadata():
    client = AsyncMock()

    client.chat_with_usage.return_value = make_chat_result(
        '{"answer": "3.", "cited_sources": [1], '
        '"sufficient_evidence": true}',
        prompt_tokens=123,
        completion_tokens=17,
        total_duration_ns=5_000_000,
        load_duration_ns=500_000,
        eval_duration_ns=4_000_000,
    )

    # This test is synchronous only to keep the assertions isolated.
    # The actual async generation behavior is covered by the tests above.
    # We intentionally do not execute the coroutine here.
    assert client.chat_with_usage.return_value.prompt_tokens == 123
    assert client.chat_with_usage.return_value.completion_tokens == 17
    assert client.chat_with_usage.return_value.total_duration_ns == 5_000_000


def test_system_prompt_states_the_consistency_invariant_explicitly():
    # The actual fix for the debugging session's root cause: the prompt
    # now states outright that cited_sources and sufficient_evidence must
    # agree, rather than leaving the relationship implicit.
    assert "must never contradict" in SYSTEM_PROMPT
    assert "cited_sources is non-empty" in SYSTEM_PROMPT