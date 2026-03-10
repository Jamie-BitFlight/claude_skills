"""Tests for token-aware batch splitting in extract_user_messages.

Verifies that:
- Single-batch output writes one JSONL file (backward compat)
- Multi-batch output splits into directory with numbered batch files
- Token counting uses tiktoken p50k_base
- Batch boundaries respect token budget
- Return value contains correct metadata
"""

from __future__ import annotations

import json
from pathlib import Path

from _server import DEFAULT_BATCH_TOKENS, EncoderCache, count_tokens, extract_user_messages


def _make_session_jsonl(path: Path, messages: list[str]) -> None:
    """Write a minimal JSONL session file with user messages.

    Args:
        path: File path to write.
        messages: List of user message strings.
    """
    with path.open("w", encoding="utf-8") as fh:
        for text in messages:
            record = {
                "type": "user",
                "message": {"content": text},
                "timestamp": "2026-03-10T00:00:00Z",
                "sessionId": "test-session",
                "uuid": "test-uuid",
                "toolUseResult": None,
            }
            fh.write(json.dumps(record) + "\n")


class TestCountTokens:
    """Tests for the _count_tokens helper."""

    def test_empty_string_returns_zero(self) -> None:
        assert count_tokens("") == 0

    def test_short_string_returns_positive(self) -> None:
        result = count_tokens("hello world")
        assert result > 0

    def test_longer_string_returns_more_tokens(self) -> None:
        short = count_tokens("hi")
        long = count_tokens("This is a much longer string with many more tokens in it.")
        assert long > short

    def test_consistent_results(self) -> None:
        text = "The quick brown fox jumps over the lazy dog."
        assert count_tokens(text) == count_tokens(text)


class TestEncoderCache:
    """Tests for the _EncoderCache singleton."""

    def test_returns_encoder(self) -> None:
        enc = EncoderCache.get()
        assert enc is not None

    def test_returns_same_instance(self) -> None:
        enc1 = EncoderCache.get()
        enc2 = EncoderCache.get()
        assert enc1 is enc2


class TestDefaultBatchTokens:
    """Tests for the default batch token constant."""

    def test_default_is_100k(self) -> None:
        assert DEFAULT_BATCH_TOKENS == 100_000


class TestExtractUserMessagesSingleBatch:
    """Tests for single-batch output (backward compatibility)."""

    async def test_single_batch_writes_one_file(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        _make_session_jsonl(session, ["Hello, how are you?", "Please help me."])

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output))

        assert result["batch_count"] == 1
        assert len(result["output_paths"]) == 1
        assert result["output_paths"][0] == str(output)
        assert output.exists()

    async def test_single_batch_jsonl_format(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        _make_session_jsonl(session, ["Hello world"])

        output = tmp_path / "output.jsonl"
        await extract_user_messages(str(session), str(output))

        lines = output.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert "text" in entry
        assert "token_count" in entry
        assert "line_index" in entry
        assert "file" in entry

    async def test_single_batch_metadata(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        msgs = ["Short message one.", "Short message two."]
        _make_session_jsonl(session, msgs)

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output))

        assert result["message_count"] == 2
        assert result["total_tokens"] > 0
        assert result["source_file"] == str(session)


class TestExtractUserMessagesMultiBatch:
    """Tests for multi-batch output with token-aware splitting."""

    async def test_multi_batch_creates_directory(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        # Create messages that exceed a tiny batch_tokens budget
        long_msg = "word " * 500  # ~500 tokens
        _make_session_jsonl(session, [long_msg, long_msg, long_msg])

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output), batch_tokens=600)

        assert result["batch_count"] > 1
        batch_dir = tmp_path / "rtfp-batches-output"
        assert batch_dir.is_dir()

    async def test_multi_batch_file_naming(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        long_msg = "word " * 500
        _make_session_jsonl(session, [long_msg, long_msg, long_msg])

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output), batch_tokens=600)

        for path_str in result["output_paths"]:
            p = Path(path_str)
            assert p.exists()
            assert p.suffix == ".jsonl"
            assert p.name.startswith("batch_")

    async def test_multi_batch_all_messages_preserved(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        long_msg = "word " * 500
        msgs = [long_msg] * 5
        _make_session_jsonl(session, msgs)

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output), batch_tokens=600)

        total_lines = 0
        for path_str in result["output_paths"]:
            content = Path(path_str).read_text(encoding="utf-8").strip()
            total_lines += len(content.split("\n"))

        assert total_lines == result["message_count"]
        assert result["message_count"] == 5

    async def test_multi_batch_respects_token_budget(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        long_msg = "word " * 500
        _make_session_jsonl(session, [long_msg, long_msg, long_msg])

        budget = 600
        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output), batch_tokens=budget)

        # Each batch file should have messages whose total tokens <= budget
        # (except when a single message exceeds budget, it gets its own batch)
        for path_str in result["output_paths"]:
            content = Path(path_str).read_text(encoding="utf-8").strip()
            lines = content.split("\n")
            batch_tokens = sum(json.loads(line)["token_count"] for line in lines)
            # A single message may exceed budget, but batch should not have
            # more than budget + one message's worth
            if len(lines) > 1:
                assert batch_tokens <= budget + max(json.loads(line)["token_count"] for line in lines)

    async def test_default_batch_tokens_produces_single_file_for_small_session(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        _make_session_jsonl(session, ["Hello", "World"])

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output))

        # With default 100k tokens, two short messages should be single batch
        assert result["batch_count"] == 1
        assert output.exists()


class TestExtractUserMessagesFiltering:
    """Tests that non-user messages are filtered out."""

    async def test_filters_assistant_messages(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        with session.open("w", encoding="utf-8") as fh:
            fh.write(
                json.dumps({
                    "type": "user",
                    "message": {"content": "Help me"},
                    "timestamp": "2026-03-10T00:00:00Z",
                    "sessionId": "s1",
                    "toolUseResult": None,
                })
                + "\n"
            )
            fh.write(
                json.dumps({
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Sure!"}]},
                    "timestamp": "2026-03-10T00:00:01Z",
                    "sessionId": "s1",
                    "toolUseResult": None,
                })
                + "\n"
            )

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output))

        assert result["message_count"] == 1

    async def test_filters_tool_use_results(self, tmp_path: Path) -> None:
        session = tmp_path / "session.jsonl"
        with session.open("w", encoding="utf-8") as fh:
            fh.write(
                json.dumps({
                    "type": "user",
                    "message": {"content": "Help me"},
                    "timestamp": "2026-03-10T00:00:00Z",
                    "sessionId": "s1",
                    "toolUseResult": None,
                })
                + "\n"
            )
            fh.write(
                json.dumps({
                    "type": "user",
                    "message": {"content": "tool output"},
                    "toolUseResult": {"type": "tool_result"},
                    "timestamp": "2026-03-10T00:00:01Z",
                    "sessionId": "s1",
                })
                + "\n"
            )

        output = tmp_path / "output.jsonl"
        result = await extract_user_messages(str(session), str(output))

        assert result["message_count"] == 1
