import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.ollama_client import ChatResult, OllamaClient
from app.evaluation.timing import StageTimer


def test_stage_timer_records_positive_elapsed_time():
    timer = StageTimer()
    with timer.track("retrieval"):
        time.sleep(0.01)
    assert timer.timings_ms["retrieval"] > 0


def test_stage_timer_accumulates_multiple_entries_of_same_stage():
    timer = StageTimer()
    with timer.track("retrieval"):
        time.sleep(0.01)
    with timer.track("retrieval"):
        time.sleep(0.01)
    # Both calls should add up, not overwrite — total should reflect ~20ms,
    # not just the second call's ~10ms.
    assert timer.timings_ms["retrieval"] >= 0.015  # allow scheduling slack


def test_stage_timer_tracks_multiple_distinct_stages_separately():
    timer = StageTimer()
    with timer.track("routing"):
        time.sleep(0.005)
    with timer.track("generation"):
        time.sleep(0.005)
    assert "routing" in timer.timings_ms
    assert "generation" in timer.timings_ms
    assert timer.total_ms >= timer.timings_ms["routing"] + timer.timings_ms["generation"] - 0.001


def test_stage_timer_still_records_when_block_raises():
    timer = StageTimer()
    with pytest.raises(ValueError):
        with timer.track("failing_stage"):
            raise ValueError("boom")
    # Timing should still be recorded even though the block raised — a
    # slow failure is still useful latency information, not something to
    # silently drop.
    assert "failing_stage" in timer.timings_ms


async def test_chat_with_usage_extracts_ollama_metadata():
    client = OllamaClient()
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "message": {"content": "The answer."},
        "prompt_eval_count": 42,
        "eval_count": 17,
        "total_duration": 123456789,
        "load_duration": 1000,
        "eval_duration": 5000,
    }

    mock_async_client = AsyncMock()
    mock_async_client.post.return_value = fake_response
    mock_async_client.__aenter__.return_value = mock_async_client
    mock_async_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        result = await client.chat_with_usage([{"role": "user", "content": "hi"}])

    assert isinstance(result, ChatResult)
    assert result.content == "The answer."
    assert result.prompt_tokens == 42
    assert result.completion_tokens == 17
    assert result.total_duration_ns == 123456789


async def test_chat_still_returns_plain_string():
    client = OllamaClient()
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "message": {"content": "plain answer"},
        "prompt_eval_count": 5,
        "eval_count": 3,
    }

    mock_async_client = AsyncMock()
    mock_async_client.post.return_value = fake_response
    mock_async_client.__aenter__.return_value = mock_async_client
    mock_async_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        result = await client.chat([{"role": "user", "content": "hi"}])

    # chat() must keep returning a plain str — every existing caller
    # (generator.py, faithfulness.py, /query's tests) depends on this.
    assert result == "plain answer"
    assert isinstance(result, str)
