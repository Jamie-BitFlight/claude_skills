#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Detect user messages containing strong emotional reactions directed at the assistant.

Stage 2 of the RTFP pipeline. Reads a single batch JSON file produced by
extract_batches.py and identifies user messages that contain frustration,
disappointment, disbelief, argument, insults, rage, or clearly negative
emotional responses directed at the assistant's output or behavior.

Uses heuristic signal detection only — no LLM calls.

Signals detected:
  - Profanity or insults directed at the assistant
  - Strong negative phrases ("wrong", "that's not", "you ignored", etc.)
  - Excessive punctuation (!!!, ???, mixed)
  - ALL CAPS words (3+ consecutive capitalized words)
  - Short messages with high emotional signal density

Output (stdout): JSON with flagged message indexes and content.
Progress/status: stderr.

Usage:
    detect_reactions.py <batch_file_path>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Signal patterns
# ---------------------------------------------------------------------------

# Phrases strongly indicating frustration/anger directed at the assistant.
# Each pattern is compiled as case-insensitive.
_NEGATIVE_PHRASE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Direct correction / disagreement
        r"\bthat'?s\s+(?:not|wrong|incorrect|broken)\b",
        r"\byou'?re\s+(?:wrong|incorrect|broken|not\s+listening)\b",
        r"\bthat\s+is\s+(?:not|wrong|incorrect|broken)\b",
        r"\byou\s+are\s+(?:wrong|incorrect|broken|not\s+listening)\b",
        r"\bno[,.]?\s+(?:that'?s|you)\b",
        r"\bno\s+no\s+no\b",
        # Imperative frustration
        r"\bstop\s+(?:doing|making|adding|changing|ignoring|it)\b",
        r"\bstop\b[.!]*$",
        r"\bdo\s+not\b.*\bagain\b",
        r"\bdon'?t\b.*\bagain\b",
        # Exasperation
        r"\bwhy\s+did\s+you\b",
        r"\bwhy\s+would\s+you\b",
        r"\bwhy\s+are\s+you\b",
        r"\bwhat\s+the\s+(?:hell|heck|fuck|actual)\b",
        r"\bare\s+you\s+(?:kidding|serious|even|listening|reading)\b",
        r"\bhow\s+many\s+times\b",
        r"\bi\s+(?:already|just)\s+(?:told|said|asked|explained)\b",
        r"\bi\s+told\s+you\b",
        r"\byou\s+ignored\b",
        r"\byou\s+missed\b",
        r"\byou\s+forgot\b",
        r"\byou\s+didn'?t\s+(?:read|listen|follow|do|check)\b",
        r"\byou\s+keep\b",
        r"\bagain\?+!*$",
        # Profanity / insults (common, non-exhaustive)
        r"\bwtf\b",
        r"\bwth\b",
        r"\bffs\b",
        r"\bomfg?\b",
        r"\bfuck(?:ing|ed)?\b",
        r"\bshit(?:ty)?\b",
        r"\bdamn\s*it\b",
        r"\bjesus\s*(?:christ)?\b",
        r"\bfor\s+(?:fuck'?s|god'?s)\s+sake\b",
        r"\bidiot\b",
        r"\bstupid\b",
        r"\buseless\b",
        r"\bhopeless\b",
        r"\bterrible\b",
        r"\bawful\b",
        r"\bgarbage\b",
        r"\btrash\b",
        r"\bjunk\b",
        # Disbelief / sarcasm
        r"\bseriously\?",
        r"\breally\?{2,}",
        r"\bunbelievable\b",
        r"\bincredible\b.*\bwrong\b",
        r"\bcome\s+on\b",
        r"\boh\s+my\s+god\b",
        r"\boh\s+come\s+on\b",
        r"\bfor\s+real\?",
    ]
]

# Regex for excessive punctuation: 3+ exclamation, 3+ question, or mixed runs.
_EXCESSIVE_PUNCT = re.compile(r"[!?]{3,}|!{2,}\?|!\?{2,}")

# Regex for ALL-CAPS words (at least 2 letters each). We look for runs of 3+.
_CAPS_WORD = re.compile(r"\b[A-Z]{2,}\b")


# ---------------------------------------------------------------------------
# Detection thresholds
# ---------------------------------------------------------------------------

_MIN_PHRASE_HITS_STANDALONE = 2  # phrase hits sufficient without other signals
_MIN_PHRASE_HITS = 1  # phrase hits needed alongside another signal
_MIN_CAPS_WORDS = 3  # non-acronym ALL-CAPS words for "shouting"
_SHORT_MESSAGE_WORDS = 15  # word count below which density matters more
_EXPECTED_ARGC = 2  # sys.argv: [script, batch_file_path]

# ---------------------------------------------------------------------------
# Signal scoring
# ---------------------------------------------------------------------------


def _count_phrase_hits(text: str) -> int:
    """Count how many distinct negative phrase patterns match in *text*.

    Returns:
        Number of distinct patterns that matched.
    """
    return sum(1 for pat in _NEGATIVE_PHRASE_PATTERNS if pat.search(text))


def _has_excessive_punctuation(text: str) -> bool:
    """Return True if *text* contains excessive punctuation runs.

    Returns:
        Whether excessive punctuation was detected.
    """
    return bool(_EXCESSIVE_PUNCT.search(text))


def _caps_word_count(text: str) -> int:
    """Count ALL-CAPS words (2+ letters) in *text*.

    Excludes common acronyms that are not emotional signals.

    Returns:
        Number of non-acronym ALL-CAPS words found.
    """
    benign_acronyms = frozenset({
        "API",
        "URL",
        "CLI",
        "JSON",
        "YAML",
        "TOML",
        "HTML",
        "CSS",
        "HTTP",
        "HTTPS",
        "SQL",
        "SSH",
        "CI",
        "CD",
        "PR",
        "MR",
        "ID",
        "UUID",
        "OK",
        "AWS",
        "GCP",
        "UI",
        "UX",
        "README",
        "TODO",
        "FIXME",
        "NOTE",
        "ENV",
        "CPU",
        "GPU",
        "RAM",
        "OS",
        "IO",
        "TCP",
        "UDP",
        "DNS",
        "TLS",
        "SSL",
        "PDF",
        "CSV",
        "XML",
        "RFC",
        "TTY",
        "PEP",
        "EOF",
        "UTF",
        "ASCII",
        "CRUD",
        "REST",
        "GRPC",
        "SDK",
        "CDN",
        "VM",
        "LLM",
        "GPT",
        "AI",
        "ML",
        "NLP",
        "STDIN",
        "STDOUT",
        "STDERR",
        "RTFP",
    })
    matches = _CAPS_WORD.findall(text)
    return sum(1 for w in matches if w not in benign_acronyms)


def is_reaction(text: str) -> bool:
    """Determine whether *text* contains a strong emotional reaction.

    A message is flagged when it meets ANY of these conditions:
      1. Two or more distinct negative-phrase pattern hits.
      2. One phrase hit AND excessive punctuation.
      3. One phrase hit AND 3+ non-acronym ALL-CAPS words.
      4. Excessive punctuation AND 3+ non-acronym ALL-CAPS words.
      5. Short message (under 15 words) with at least one phrase hit.

    Returns:
        True if the message should be flagged.
    """
    phrase_hits = _count_phrase_hits(text)
    excessive_punct = _has_excessive_punctuation(text)
    caps_count = _caps_word_count(text)
    word_count = len(text.split())

    # Condition 1: multiple phrase hits — strong signal on its own
    if phrase_hits >= _MIN_PHRASE_HITS_STANDALONE:
        return True

    # Condition 5: short message with any phrase hit (high density)
    if phrase_hits >= _MIN_PHRASE_HITS and word_count < _SHORT_MESSAGE_WORDS:
        return True

    # Condition 2: phrase hit + excessive punctuation
    if phrase_hits >= _MIN_PHRASE_HITS and excessive_punct:
        return True

    # Condition 3: phrase hit + caps shouting
    if phrase_hits >= _MIN_PHRASE_HITS and caps_count >= _MIN_CAPS_WORDS:
        return True

    # Condition 4: punctuation + caps shouting (no phrase needed)
    return bool(excessive_punct and caps_count >= _MIN_CAPS_WORDS)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def detect_reactions(batch: dict) -> dict:
    """Process a batch dict and return flagged messages.

    Args:
        batch: Parsed batch JSON with "messages" list, "source_file", etc.

    Returns:
        Result dict with "batch_file", "source_file", "flagged_count",
        and "flagged" list.
    """
    messages: list[dict] = batch.get("messages", [])
    source_file: str = batch.get("source_file", "")
    flagged: list[dict] = []

    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        if is_reaction(content):
            flagged.append({
                "index": msg.get("index"),
                "source_file": msg.get("source_file", source_file),
                "timestamp": msg.get("timestamp", ""),
                "content": content,
            })

    return {
        "batch_file": "",  # Caller sets this after knowing the path
        "source_file": source_file,
        "flagged_count": len(flagged),
        "flagged": flagged,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Read a batch JSON file and output flagged reaction messages as JSON."""
    if len(sys.argv) != _EXPECTED_ARGC or sys.argv[1] in {"-h", "--help"}:
        print(f"Usage: {sys.argv[0]} <batch_file_path>", file=sys.stderr)
        sys.exit(_EXPECTED_ARGC if len(sys.argv) != _EXPECTED_ARGC else 0)

    batch_path = Path(sys.argv[1])
    if not batch_path.exists():
        print(f"Error: file not found: {batch_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading batch from {batch_path.name}...", file=sys.stderr)

    try:
        with batch_path.open(encoding="utf-8") as fh:
            batch = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading batch file: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(batch, dict) or "messages" not in batch:
        print("Error: batch file missing 'messages' key", file=sys.stderr)
        sys.exit(1)

    msg_count = len(batch.get("messages", []))
    print(f"Scanning {msg_count} messages for emotional reactions...", file=sys.stderr)

    result = detect_reactions(batch)
    result["batch_file"] = str(batch_path)

    print(f"Flagged {result['flagged_count']} of {msg_count} messages.", file=sys.stderr)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()  # trailing newline


if __name__ == "__main__":
    main()
