#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb>=1.0.0",
#   "tiktoken>=0.7.0",
# ]
# ///
"""Extract and batch user-authored messages from a Claude Code session JSONL file.

Reads ONLY user-authored messages from the given JSONL file — no assistant
messages, tool outputs, system messages, or developer messages. Batch files
are for emotional-reply detection only; full transcript context is retrieved
later during reconstruction.

Each entry preserves its source session file path and original message index
so it can be traced back to the full transcript.

Splits into batch files of approximately TARGET_TOKENS tokens each (default
100k tokens). Token counting uses tiktoken p50k_base encoding (recommended approximation for Claude).

Each batch file is a JSON object:
{
  "source_file": "/path/to/session.jsonl",
  "session_id": "uuid",
  "batch_index": 0,
  "total_batches": N,
  "messages": [
    {
      "index": 0,
      "source_file": "/path/to/session.jsonl",
      "timestamp": "...",
      "content": "...",
      "token_count": N
    },
    ...
  ]
}

Usage:
    extract_batches.py <session_jsonl_path> [--out-dir <tempdir>/rtfp-batches] [--batch-tokens 100000]
    extract_batches.py <session_jsonl_path> --list-only
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import duckdb
import tiktoken

_TIKTOKEN_ENCODING = "p50k_base"


class _EncoderCache:
    enc: tiktoken.Encoding | None = None

    @classmethod
    def get(cls) -> tiktoken.Encoding:
        if cls.enc is None:
            cls.enc = tiktoken.get_encoding(_TIKTOKEN_ENCODING)
        return cls.enc


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken p50k_base encoding (Claude approximation).

    Returns:
        Number of tokens in the text.
    """
    return len(_EncoderCache.get().encode(text))


_NOISE_PREFIXES = (
    "<local-command-caveat>",
    "<bash-stdout>",
    "<tool_use_error>",
    "<task-notification>",
    "<command-message>",
    "<system-reminder>",
)


def _extract_text(content: str | list | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for element in content:
        if isinstance(element, dict) and element.get("type") == "text":
            text = element.get("text")
            if isinstance(text, str):
                parts.append(text)
        elif isinstance(element, dict) and element.get("type") == "tool_result":
            # Include tool result content for context
            inner = element.get("content", "")
            inner_text = _extract_text(inner)
            if inner_text:
                parts.append(f"[tool_result: {inner_text}]")
    return "\n".join(parts)


def _is_noise(text: str) -> bool:
    stripped = text.lstrip()
    return any(stripped.startswith(p) for p in _NOISE_PREFIXES)


def load_messages(session_path: Path) -> list[dict]:
    """Load user-authored messages only from a JSONL session file.

    Uses DuckDB ``read_ndjson()`` as the query layer for all JSONL reads.
    Excludes assistant messages, tool outputs, system messages, and developer
    messages. Each entry preserves source_file and index for later trace-back
    to the full transcript during reconstruction.

    Returns:
        List of user message dicts with keys: index, source_file, timestamp,
        content, token_count.
    """
    messages: list[dict] = []
    msg_index = 0
    source_file = str(session_path)

    conn = duckdb.connect()
    try:
        rows = conn.execute(
            "SELECT to_json(t) AS raw FROM read_ndjson(?, ignore_errors := true, maximum_object_size := 67108864) t",
            [str(session_path)],
        ).fetchall()
    except duckdb.Error:
        conn.close()
        return messages
    finally:
        conn.close()

    for (raw_json,) in rows:
        try:
            rec = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(rec, dict):
            continue

        # User messages only — assistant/tool/system entries are excluded
        if rec.get("type") != "user":
            continue

        # Skip tool result lines (infrastructure, not user-authored)
        if rec.get("toolUseResult") is not None:
            continue

        content = _extract_text(rec.get("message", {}).get("content"))
        if not content or _is_noise(content):
            continue

        messages.append({
            "index": msg_index,
            "source_file": source_file,
            "timestamp": rec.get("timestamp", ""),
            "content": content,
            "token_count": count_tokens(content),
        })
        msg_index += 1

    return messages


def split_into_batches(messages: list[dict], target_tokens: int) -> list[list[dict]]:
    """Split messages into batches not exceeding target_tokens total.

    Returns:
        List of message batches, each batch being a list of message dicts.
    """
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_tokens = 0

    for msg in messages:
        tokens = msg["token_count"]
        # Start new batch if we'd exceed target and current batch is non-empty
        if current_tokens + tokens > target_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(msg)
        current_tokens += tokens

    if current_batch:
        batches.append(current_batch)

    return batches


def write_batch_files(session_path: Path, session_id: str, batches: list[list[dict]], out_dir: Path) -> list[Path]:
    """Write batch JSON files and return their paths.

    Returns:
        List of Path objects for each written batch file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    total = len(batches)

    for i, batch in enumerate(batches):
        payload = {
            "source_file": str(session_path),
            "session_id": session_id,
            "batch_index": i,
            "total_batches": total,
            "message_count": len(batch),
            "total_tokens": sum(m["token_count"] for m in batch),
            "messages": batch,
        }
        out_path = out_dir / f"batch_{i:03d}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        written.append(out_path)
        print(
            f"  Batch {i}: {len(batch)} user messages, {payload['total_tokens']:,} tokens → {out_path}", file=sys.stderr
        )

    return written


_DEFAULT_OUT_DIR = str(Path(tempfile.gettempdir()) / "rtfp-batches")


def main() -> None:
    """Extract and batch messages from a Claude Code session JSONL file."""
    parser = argparse.ArgumentParser(description="Extract and batch Claude Code session messages")
    parser.add_argument("session_path", help="Path to session .jsonl file")
    parser.add_argument("--out-dir", default=_DEFAULT_OUT_DIR, help="Output directory for batch files")
    parser.add_argument(
        "--batch-tokens",
        type=int,
        default=100_000,
        help="Target tokens per batch (tiktoken cl100k_base). Default: 100000",
    )
    parser.add_argument(
        "--list-only", action="store_true", help="Print message count and estimated batches without writing files"
    )
    args = parser.parse_args()

    session_path = Path(args.session_path)
    if not session_path.exists():
        print(f"Error: file not found: {session_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading messages from {session_path.name}...", file=sys.stderr)
    messages = load_messages(session_path)

    if not messages:
        print("No messages found in session file.", file=sys.stderr)
        sys.exit(1)

    total_tokens = sum(m["token_count"] for m in messages)
    estimated_batches = max(1, (total_tokens + args.batch_tokens - 1) // args.batch_tokens)

    print(f"User messages: {len(messages)}", file=sys.stderr)
    print(f"Total tokens: {total_tokens:,} (tiktoken cl100k_base)", file=sys.stderr)
    print(f"Estimated batches at {args.batch_tokens:,} tokens each: {estimated_batches}", file=sys.stderr)

    if args.list_only:
        result = {
            "session_path": str(session_path),
            "session_id": session_path.stem,
            "user_message_count": len(messages),
            "total_tokens": total_tokens,
            "estimated_batches": estimated_batches,
        }
        print(json.dumps(result, indent=2))
        return

    batches = split_into_batches(messages, args.batch_tokens)
    out_dir = Path(args.out_dir)

    print(f"\nWriting {len(batches)} batch file(s) to {out_dir}...", file=sys.stderr)
    written = write_batch_files(session_path, session_path.stem, batches, out_dir)

    result = {
        "session_id": session_path.stem,
        "source_file": str(session_path),
        "out_dir": str(out_dir),
        "batch_files": [str(p) for p in written],
        "batch_count": len(written),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
