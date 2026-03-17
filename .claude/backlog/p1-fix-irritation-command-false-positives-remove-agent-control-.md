---
name: Fix irritation command false positives — remove agent-control words from correction phrases
description: <div><sub>2026-03-11T19:47:34Z</sub>
metadata:
  topic: fix-irritation-command-false-positives-remove-agent-control-
  source: User feedback — 2026-03-11
  added: '2026-03-11'
  priority: P1
  type: Bug
  status: in-progress
  issue: '#610'
  groomed: '2026-03-11'
  last_synced: '2026-03-14T15:59:45Z'
  plan: plan/tasks-5-irritation-llm-fix.md
---

## Fact-Check

<div><sub>2026-03-11T19:47:34Z</sub>

Claims checked: 3
VERIFIED: 2 | REFUTED: 0 | INCONCLUSIVE: 1

- VERIFIED: `_CORRECTION_PHRASES` constant exists in `session_query.py` at lines 71–82
- VERIFIED: Contains "stop", "undo", "revert", "don't", "no," (all named phrases present)
- INCONCLUSIVE: Claim that no JSONL analysis was done — no commit evidence of data-driven selection, but absence of commits is not conclusive proof

</div>

## RT-ICA

<div><sub>2026-03-11T19:47:45Z</sub>

Goal: Replace speculative correction phrase list with data-driven set that reliably signals user frustration without matching ordinary conversational messages.

Conditions:
1. _CORRECTION_PHRASES constant exists with false-positive-prone terms | AVAILABLE (VERIFIED)
2. Session JSONL files accessible for sampling | DERIVABLE (known path pattern from session-historian)
3. Existing JSONL parser infrastructure in session_query.py | DERIVABLE (file already parses JSONL)
4. Acceptance criteria / precision threshold for a reliable phrase | MISSING
5. Known false-positive phrases documented | DERIVABLE (can be sampled from recent sessions)

Decision: APPROVED
Missing: Precision threshold — what false-positive rate is acceptable before a phrase qualifies

</div>

## Groomed (2026-03-11)

### Issue Classification

<div><sub>2026-03-11T19:47:55Z</sub>

Type: defect
Scenario: Irritation command fires on neutral messages containing "stop", "undo", "revert", "don't", "wrong", "no," in non-frustration contexts (e.g., "don't use tabs", "revert to the original approach", "stop after step 3")
Target: Eliminate false positives for bare-token entries while preserving detection of genuine frustration signals
Analysis method: 5-whys

Root Cause: The phrase list was authored by enumerating frustration-adjacent vocabulary without measuring false-positive rate against real session data, so it contains tokens whose base-rate occurrence in neutral messages far exceeds their occurrence in frustrated ones.

Fix Direction: Replace bare-token entries with longer, specific multi-word phrases that only occur in correction contexts, OR add discriminating context checks (word-boundary matching with \b, minimum message length, sliding-window requiring co-occurrence of multiple signals).

</div>

### Reproducibility

<div><sub>2026-03-11T19:50:32Z</sub>

Trigger using any session JSONL file available on this machine:

```bash
uv run .claude/skills/session-historian/scripts/session_query.py irritation <session-file-or-project-slug>
```

Concrete false-positive examples — these messages match and should not:

- `"don't use tabs, use spaces"` — matches on `"don't"` (substring of `"don't use tabs"`)
- `"revert to the original approach"` — matches on `"revert"`
- `"stop after step 3"` — matches on `"stop"`
- `"undo the last change and try again"` — matches on `"undo"`
- `"that's wrong direction but the concept is right"` — matches on `"wrong"` and `"that's wrong"`
- `"no, wait — actually that's correct"` — matches on `"no,"` (trailing comma is in the phrase)

The matching logic at lines 1046–1050 of `session_query.py` performs a bare `phrase in lower` substring check with no word-boundary guard and no minimum message length. The first phrase that matches fires and breaks — meaning a single token match on `"stop"` in any position classifies the entire message as an irritation signal.

No automated test currently exercises `_collect_irritation_signals()` against neutral messages.
</div>

<div><sub>2026-03-11T19:52:56Z</sub>

The matcher at lines 1046–1050 of session_query.py performs `if phrase in lower` — bare substring, no word-boundary, no length guard.

Concrete false-positive examples (all fire the irritation command incorrectly):
- "don't use tabs" → matches "don't"
- "stop after step 3" → matches "stop"
- "revert to the original approach" → matches "revert"
- "undo the last change and try again" → matches "undo"
- "wrong file — I meant the other one" → matches "wrong"
- "no, that makes sense" → matches "no,"

Any user message containing these tokens in a neutral instruction context will be counted as a frustration signal.

</div>

### Priority

<div><sub>2026-03-11T19:50:49Z</sub>

8/10 — The `irritation` command was introduced specifically to surface friction signals from session data. If bare tokens like `"stop"`, `"undo"`, `"revert"`, and `"don't"` fire on neutral instruction text, the command produces a noisy list dominated by false positives. A developer running `irritation` to identify pain points gets misleading output and cannot trust the signal. This directly degrades the tool's primary value.

Phrase-by-phrase false-positive risk assessment (all 10 entries):

| Phrase | Risk | Reason |
|---|---|---|
| `"stop"` | HIGH | Appears constantly in instructions: "stop after", "stop the loop", "don't stop" |
| `"undo"` | HIGH | Standard git/editor vocabulary: "undo the last change", "undo migration" |
| `"revert"` | HIGH | Standard git vocabulary: "revert this commit", "revert to approach X" |
| `"don't"` | HIGH | Appears in ~50% of constraining instructions: "don't use tabs", "don't add comments" |
| `"no,"` | HIGH | Conversational connector: "no, wait — that's right", "no, we should" |
| `"wrong"` | MEDIUM | More specific but still fires on: "wrong direction but…", "nothing wrong with" |
| `"incorrect"` | LOW | Less common in neutral text; genuinely signals correction |
| `"that's wrong"` | LOW | Multi-word; rarely appears in neutral instruction text |
| `"that's not"` | LOW | Multi-word; signals redirection |
| `"not what i asked"` | LOW | Multi-word; unambiguously a correction signal |

5 of 10 phrases are HIGH false-positive risk. The 4 multi-word phrases ("that's wrong", "not what i asked", "that's not", and marginally "incorrect") are likely genuine signals.
</div>

<div><sub>2026-03-11T19:53:07Z</sub>

P1 — correct. The irritation command output is used for session quality analysis. False positives erode trust in the metric: if 5 of 10 detection phrases fire on neutral instruction text, the count returned is meaningless as a frustration signal.

Phrase-by-phrase risk assessment:
- HIGH false-positive risk (bare tokens): "stop", "undo", "revert", "don't", "no,"
- LOW false-positive risk (multi-word, specific): "that's wrong", "not what i asked", "that's not", "wrong", "incorrect"

"wrong" and "incorrect" are borderline — single-word but less common in neutral instruction contexts than "stop"/"don't".

The 5 high-risk entries are the primary fix target.

</div>

### Impact

<div><sub>2026-03-11T19:51:00Z</sub>

- Blocks: Any developer relying on `irritation` output to understand friction in their Claude sessions. The output is untrustworthy until fixed.
- Bottleneck: The `irritation` command is one of four new commands added by the `session-historian-enhance` feature (#599). That feature was specifically about making session analysis useful. A false-positive rate this high on the irritation signal undermines the feature's stated goal.
- Related: #607 (add unit tests for session-historian) depends on stable, correct behavior in `_collect_irritation_signals()`. Writing tests before fixing the false positives would codify the wrong behavior.
- Dependency direction: This item should be resolved before #607 (tests) writes coverage for the irritation helpers — otherwise tests will be written against the broken phrase list.
</div>

### Benefits

<div><sub>2026-03-11T19:51:09Z</sub>

- `irritation` output becomes a trustworthy signal developers can act on
- Unblocks accurate test coverage for `_collect_irritation_signals()` in #607
- Establishes a data-driven baseline for the phrase list — future phrase changes can be validated against sampled JSONL before merging
</div>

### Expected Behavior

<div><sub>2026-03-11T19:51:20Z</sub>

The `irritation` command should return only messages where the user is expressing frustration, correction, or displeasure directed at Claude's output or behavior. Messages that contain those words in neutral, instructional, or technical contexts should not be returned.

A message like `"don't use tabs, use spaces"` is a preference instruction. A message like `"that's wrong, revert the file and start over"` is a genuine correction signal. The command should distinguish these.
</div>

### Desired Structure

<div><sub>2026-03-11T19:51:31Z</sub>

The `_CORRECTION_PHRASES` constant contains only phrases that reliably distinguish correction/frustration from neutral instruction text. The bare single-token entries that fire on ordinary messages (`"stop"`, `"undo"`, `"revert"`, `"don't"`, `"no,"`) are either removed or replaced with longer, more specific multi-word variants.

The description item notes two valid fix directions:
1. Replace bare tokens with specific multi-word phrases that only appear in correction contexts
2. Add discriminating context checks (word-boundary `\b`, minimum message length, co-occurrence scoring)

Which direction to take requires sampling real session JSONL to understand how frequently the high-risk phrases appear in neutral vs. frustrated messages. That sampling is a prerequisite to any phrase list change — the description is explicit on this point: "The fix should be driven by observed data, not a revised guess at a better list."
</div>

### Acceptance Criteria

<div><sub>2026-03-11T19:51:43Z</sub>

1. Sample at least 3 real session JSONL files and run each of the 10 phrases through the messages. Document how many matches are neutral vs. correction-intent for each phrase.
2. The 5 HIGH false-positive-risk phrases (`"stop"`, `"undo"`, `"revert"`, `"don't"`, `"no,"`) are either removed from `_CORRECTION_PHRASES` or replaced with longer, context-specific variants that do not fire on neutral instruction text.
3. Running `uv run session_query.py irritation <session-file>` against a session containing `"don't use tabs"`, `"revert to the original approach"`, and `"stop after step 3"` returns no irritation hits for those messages.
4. Running the same command against a session containing `"that's wrong, start over"`, `"not what i asked"`, and `"undo that, it broke the build"` still returns hits for those messages.
5. `ruff check` and `ty check` pass on the modified file.
6. The updated phrase list is accompanied by a comment citing the session sampling that justified each retained or new phrase.
</div>

### Resources

<div><sub>2026-03-11T19:51:55Z</sub>

| Type | Item |
|------|------|
| Source file | `.claude/skills/session-historian/scripts/session_query.py` (lines 71–82: `_CORRECTION_PHRASES`; lines 1028–1051: `_collect_irritation_signals()`) |
| Related backlog | #607 — Add unit tests for session-historian (depends on this fix being correct before tests are written) |
| Related backlog | #599 — session-historian-enhance (parent feature that introduced irritation command) |
| Plan artifact | `plan/tasks-6-session-historian-enhance.md` (original implementation plan) |
| Plan artifact | `plan/tasks-34-session-historian-enhance-followup-1.md` (follow-up test plan) |
| Agent | `@python3-development:python-cli-architect` — implement phrase list change |
| Agent | `@python3-development:python-pytest-architect` — write/update tests after fix |
</div>

### Dependencies

<div><sub>2026-03-11T19:52:03Z</sub>

- Depends on: None — the fix is self-contained within `session_query.py`. Real session JSONL data is available on this machine via the paths that `_resolve_session()` already knows about.
- Blocks: #607 (add unit tests for session-historian) — tests for `_collect_irritation_signals()` should not be written against the current broken phrase list.
</div>

<div><sub>2026-03-11T19:53:29Z</sub>

Blocks: #607 (add tests for session_query.py) — tests must be written after the phrase list is fixed

Requires before implementation:
1. Human routing decision: approach A (replace bare tokens with multi-word phrases) vs approach B (add word-boundary + length guards)
2. Human decision: acceptable precision threshold (what false-positive rate qualifies a phrase?)
3. Data sampling step: examine 5–10 real session JSONL files to verify which phrases actually appear in frustration contexts

</div>

### Blockers

<div><sub>2026-03-11T19:52:11Z</sub>

- No hard blockers. One open question: the precision threshold (what false-positive rate is acceptable for a phrase to remain in the list) is not specified. The implementer must either: (a) sample real session data and report findings for human review before pruning, or (b) apply a conservative rule — keep only phrases that require more than one word AND cannot plausibly appear in a neutral instruction.

The description explicitly says: "The fix should be driven by observed data, not a revised guess at a better list." This means data sampling is a required first step, not optional.
</div>

### Questions for Human

<div><sub>2026-03-11T19:52:20Z</sub>

- Precision threshold: What false-positive rate is acceptable? Should a phrase that matches 70% neutral / 30% frustrated be kept, or is that too noisy? Or should the rule be simpler — "only multi-word phrases that cannot appear in neutral instruction text"?
- Fix approach: Prefer (A) remove bare tokens and replace with multi-word variants, or (B) keep bare tokens but add word-boundary / context guards (`re.search(r'\bstop\b')` + minimum message length)? Both are valid but have different complexity trade-offs.
</div>

### Effort

<div><sub>2026-03-11T19:52:29Z</sub>

Small — The code change itself is a constant list edit in one file. The non-trivial part is the required data-sampling step: reading real session JSONL, running the current phrases, and counting neutral vs. correction matches per phrase. That analysis is an hour of work at most. The actual phrase list edit and linting pass is 15 minutes.
</div>

### Scope

<div><sub>2026-03-11T19:53:20Z</sub>

Small — single file change.

Files to change:
- `.claude/skills/session-historian/scripts/session_query.py` — modify `_CORRECTION_PHRASES` and optionally the matcher function

No test file exists for session_query.py (confirmed by glob search). Backlog item #607 tracks adding tests — this item blocks #607 because tests written against the current phrase list would codify wrong behavior.

The description requires the fix to be data-driven: sample real session JSONL files first, examine how each phrase actually appears in context, then revise the list. This sampling step is the bulk of the work.

Two fix approaches (design decision required before implementation):
A. Remove bare-token entries; replace with longer specific phrases ("no, that's wrong", "stop — ", etc.)
B. Keep phrase list but add word-boundary matching (re.search with \b) + minimum message length guard

</div>

### Skills

<div><sub>2026-03-11T19:53:37Z</sub>

- python3-development:python-cli-architect — implement the phrase list fix and matcher update
- python3-development:python-pytest-architect — write tests after fix (coordinate with #607)
- session-historian — context on JSONL format and session data paths for sampling step

</div>

### Prior Work

<div><sub>2026-03-11T19:53:45Z</sub>

- commit e3872571: "feat(session-historian): add four new query commands (errors, tools, irritation, current-path)" — original implementation that introduced _CORRECTION_PHRASES
- commit 781ef12e: "feat(session-historian): enhance session_query.py with new query commands" — subsequent enhancement, phrase list unchanged
- No prior fix attempts found

</div>

### Decision

<div><sub>2026-03-11T20:06:23Z</sub>

Approach confirmed by user (2026-03-11): Replace `_CORRECTION_PHRASES` substring matching with LLM judgment — same pattern as the frustration-analyzer batch-detector subagent. No phrase list. Claude API reads each user message and decides if it is a genuine correction/frustration signal.

Reference implementation: `plugins/frustration-analyzer/agents/frustration-analyst.md` — batch-detector stage.

Rationale: Phrase matching cannot discriminate context. LLM judgment handles "don't use tabs" vs "don't do that again" naturally without a maintained list.

</div>
