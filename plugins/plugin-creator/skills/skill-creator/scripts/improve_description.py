#!/usr/bin/env python3
"""Improve a skill description based on eval results.

Takes eval results (from run_eval.py) and generates an improved description
using Claude with extended thinking.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import anthropic
from anthropic.types import TextBlock, ThinkingBlock

from scripts.utils import parse_skill_md

if TYPE_CHECKING:
    from anthropic.types import MessageParam

MAX_DESCRIPTION_CHARS = 1024


def _build_prompt(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    test_results: dict | None,
) -> str:
    """Build the improvement prompt from eval results and history.

    Args:
        skill_name: Name of the skill being optimised.
        skill_content: Full SKILL.md content for context.
        current_description: The description currently in use.
        eval_results: Eval results dict from run_eval.py.
        history: Previous improvement attempts.
        test_results: Optional test-set eval results.

    Returns:
        The formatted prompt string ready to send to Claude.
    """
    failed_triggers = [r for r in eval_results["results"] if r["should_trigger"] and not r["pass"]]
    false_triggers = [r for r in eval_results["results"] if not r["should_trigger"] and not r["pass"]]

    train_score = f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"
    if test_results:
        test_score = f"{test_results['summary']['passed']}/{test_results['summary']['total']}"
        scores_summary = f"Train: {train_score}, Test: {test_score}"
    else:
        scores_summary = f"Train: {train_score}"

    prompt = f"""You are optimizing a skill description for a Claude Code skill called "{skill_name}". A "skill" is sort of like a prompt, but with progressive disclosure -- there's a title and description that Claude sees when deciding whether to use the skill, and then if it does use the skill, it reads the .md file which has lots more details and potentially links to other resources in the skill folder like helper files and scripts and additional documentation or examples.

The description appears in Claude's "available_skills" list. When a user sends a query, Claude decides whether to invoke the skill based solely on the title and on this description. Your goal is to write a description that triggers for relevant queries, and doesn't trigger for irrelevant ones.

Here's the current description:
<current_description>
"{current_description}"
</current_description>

Current scores ({scores_summary}):
<scores_summary>
"""

    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat these — try something structurally different):\n\n"
        for h in history:
            train_s = f"{h.get('train_passed', h.get('passed', 0))}/{h.get('train_total', h.get('total', 0))}"
            test_s = (
                f"{h.get('test_passed', '?')}/{h.get('test_total', '?')}" if h.get("test_passed") is not None else None
            )
            score_str = f"train={train_s}" + (f", test={test_s}" if test_s else "")
            prompt += f"<attempt {score_str}>\n"
            prompt += f'Description: "{h["description"]}"\n'
            if "results" in h:
                prompt += "Train results:\n"
                for r in h["results"]:
                    status = "PASS" if r["pass"] else "FAIL"
                    prompt += f'  [{status}] "{r["query"][:80]}" (triggered {r["triggers"]}/{r["runs"]})\n'
            if h.get("note"):
                prompt += f"Note: {h['note']}\n"
            prompt += "</attempt>\n\n"

    prompt += f"""</scores_summary>

Skill content (for context on what the skill does):
<skill_content>
{skill_content}
</skill_content>

Based on the failures, write a new and improved description that is more likely to trigger correctly. When I say "based on the failures", it's a bit of a tricky line to walk because we don't want to overfit to the specific cases you're seeing. So what I DON'T want you to do is produce an ever-expanding list of specific queries that this skill should or shouldn't trigger for. Instead, try to generalize from the failures to broader categories of user intent and situations where this skill would be useful or not useful. The reason for this is twofold:

1. Avoid overfitting
2. The list might get loooong and it's injected into ALL queries and there might be a lot of skills, so we don't want to blow too much space on any given description.

Concretely, your description should not be more than about 100-200 words, even if that comes at the cost of accuracy.

Here are some tips that we've found to work well in writing these descriptions:
- The skill should be phrased in the imperative -- "Use this skill for" rather than "this skill does"
- The skill description should focus on the user's intent, what they are trying to achieve, vs. the implementation details of how the skill works.
- The description competes with other skills for Claude's attention — make it distinctive and immediately recognizable.
- If you're getting lots of failures after repeated attempts, change things up. Try different sentence structures or wordings.

I'd encourage you to be creative and mix up the style in different iterations since you'll have multiple opportunities to try different approaches and we'll just grab the highest-scoring one at the end.

Please respond with only the new description text in <new_description> tags, nothing else."""

    return prompt


def _call_claude(client: anthropic.Anthropic, model: str, messages: list[MessageParam]) -> tuple[str, str]:
    """Call Claude and extract thinking and text blocks from the response.

    Args:
        client: Authenticated Anthropic client.
        model: Model identifier string.
        messages: List of message dicts to send.

    Returns:
        Tuple of (thinking_text, response_text).
    """
    response = client.messages.create(
        model=model, max_tokens=16000, thinking={"type": "enabled", "budget_tokens": 10000}, messages=messages
    )
    thinking_text = ""
    text = ""
    for block in response.content:
        if isinstance(block, ThinkingBlock):
            thinking_text = block.thinking
        elif isinstance(block, TextBlock):
            text = block.text
    return thinking_text, text


def _extract_description(text: str) -> str:
    """Extract the description from <new_description> tags or fall back to full text.

    Args:
        text: Raw response text from Claude.

    Returns:
        Cleaned description string.
    """
    match = re.search(r"<new_description>(.*?)</new_description>", text, re.DOTALL)
    return match.group(1).strip().strip('"') if match else text.strip().strip('"')


def _shorten_if_needed(
    client: anthropic.Anthropic, model: str, prompt: str, initial_text: str, description: str, transcript: dict
) -> str:
    """Shorten description if it exceeds the character limit.

    Args:
        client: Authenticated Anthropic client.
        model: Model identifier string.
        prompt: Original user prompt (used as conversation context).
        initial_text: Claude's initial assistant response text.
        description: Parsed description that may be over the limit.
        transcript: Mutable transcript dict to record rewrite details.

    Returns:
        Shortened description if over the limit, otherwise the original.
    """
    if len(description) <= MAX_DESCRIPTION_CHARS:
        return description

    shorten_prompt = (
        f"Your description is {len(description)} characters, which exceeds the hard "
        f"{MAX_DESCRIPTION_CHARS} character limit. Please rewrite it to be under "
        f"{MAX_DESCRIPTION_CHARS} characters while preserving the most important trigger "
        "words and intent coverage. Respond with only the new description in <new_description> tags."
    )
    shorten_thinking, shorten_text = _call_claude(
        client,
        model,
        [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": initial_text},
            {"role": "user", "content": shorten_prompt},
        ],
    )
    shortened = _extract_description(shorten_text)

    transcript["rewrite_prompt"] = shorten_prompt
    transcript["rewrite_thinking"] = shorten_thinking
    transcript["rewrite_response"] = shorten_text
    transcript["rewrite_description"] = shortened
    transcript["rewrite_char_count"] = len(shortened)

    return shortened


def _log_transcript(transcript: dict, log_dir: Path | None, iteration: int | None) -> None:
    """Write the transcript JSON to the log directory if configured.

    Args:
        transcript: Transcript dict to serialise.
        log_dir: Directory to write logs into, or None to skip.
        iteration: Iteration number used in the filename, or None.
    """
    if not log_dir:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
    log_file.write_text(json.dumps(transcript, indent=2))


def improve_description(
    client: anthropic.Anthropic,
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str,
    test_results: dict | None = None,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Call Claude to improve the description based on eval results.

    Args:
        client: Authenticated Anthropic client.
        skill_name: Name of the skill being optimised.
        skill_content: Full SKILL.md content for context.
        current_description: The description currently in use.
        eval_results: Eval results dict from run_eval.py.
        history: Previous improvement attempts.
        model: Model identifier string.
        test_results: Optional test-set eval results.
        log_dir: Directory to write transcript logs into, or None to skip.
        iteration: Iteration number used in log filenames.

    Returns:
        The improved description string.
    """
    prompt = _build_prompt(skill_name, skill_content, current_description, eval_results, history, test_results)

    thinking_text, text = _call_claude(client, model, [{"role": "user", "content": prompt}])
    description = _extract_description(text)

    transcript: dict = {
        "iteration": iteration,
        "prompt": prompt,
        "thinking": thinking_text,
        "response": text,
        "parsed_description": description,
        "char_count": len(description),
        "over_limit": len(description) > MAX_DESCRIPTION_CHARS,
    }

    description = _shorten_if_needed(client, model, prompt, text, description, transcript)
    transcript["final_description"] = description

    _log_transcript(transcript, log_dir, iteration)

    return description


def main() -> None:
    """Parse arguments, run description improvement, and print JSON output."""
    parser = argparse.ArgumentParser(description="Improve a skill description based on eval results")
    parser.add_argument("--eval-results", required=True, help="Path to eval results JSON (from run_eval.py)")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--history", default=None, help="Path to history JSON (previous attempts)")
    parser.add_argument("--model", required=True, help="Model for improvement")
    parser.add_argument("--verbose", action="store_true", help="Print thinking to stderr")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_results = json.loads(Path(args.eval_results).read_text(encoding="utf-8"))
    history: list[dict] = []
    if args.history:
        history = json.loads(Path(args.history).read_text(encoding="utf-8"))

    name, _, content = parse_skill_md(skill_path)
    current_description = eval_results["description"]

    if args.verbose:
        print(f"Current: {current_description}", file=sys.stderr)
        print(f"Score: {eval_results['summary']['passed']}/{eval_results['summary']['total']}", file=sys.stderr)

    client = anthropic.Anthropic()
    new_description = improve_description(
        client=client,
        skill_name=name,
        skill_content=content,
        current_description=current_description,
        eval_results=eval_results,
        history=history,
        model=args.model,
    )

    if args.verbose:
        print(f"Improved: {new_description}", file=sys.stderr)

    output = {
        "description": new_description,
        "history": [
            *history,
            {
                "description": current_description,
                "passed": eval_results["summary"]["passed"],
                "failed": eval_results["summary"]["failed"],
                "total": eval_results["summary"]["total"],
                "results": eval_results["results"],
            },
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
