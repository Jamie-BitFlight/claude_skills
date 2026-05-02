# Improvement Proposals: ESP-CLAW

**Research entry**: ./research/agent-frameworks/esp-claw.md
**Generated**: 2026-05-02
**Patterns assessed**: 7
**Backlog items created**: 1 (issues: #2097)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Add semantic (paraphrase) deduplication to research-curator entry creation

**Source pattern**: "Semantic deduplication via embedding-free cosine similarity (avoids expensive embedding model). Cosine similarity >0.9 considered duplicates. Prevents memory bloat from paraphrased facts." — Technical Architecture / Long-Term Memory Manager and Memory Optimization Techniques sections of ESP-CLAW research entry.
**Local system**: ./.claude/skills/research-curator/references/batch-mode.md (lines 31, 67)
**Confidence**: High
**Impact**: Medium
**Backlog**: #2097 created

### Current state

`./.claude/skills/research-curator/references/batch-mode.md` line 67 specifies: "Before spawning, check if `./research/` already contains an entry for the URL's resource. If found, skip with info message suggesting `--rerun` instead." Verified by Grep: only `batch-mode.md` line 31 mentions "deduplicated URLs" — deduplication is purely URL-string-based. Grep of `.claude/skills/research-curator/` for `cosine`, `similarity`, `semantic`, or `paraphrase` returns zero matches. The validate_research.py script and `@research-curator` agent perform no title/topic similarity check.

Symptom: two batch invocations targeting the same underlying resource via different URLs (e.g., `https://github.com/espressif/esp-claw` and `https://esp-claw.com/`, or a mirror site and the canonical site) will both pass the URL-equality check and produce two separate entries describing the same project. The same applies to URL canonicalization variants (trailing slash, http vs https, www vs apex). The vault accumulates near-duplicate entries that fragment cross-references and waste reader time.

### Target state

`./.claude/skills/research-curator/references/batch-mode.md` Wave Spawning step (the URL deduplication node) and the corresponding pre-spawn check delegate to a new helper `scripts/check_resource_duplicates.py` that performs:

1. URL canonicalization (lowercase host, strip trailing slash, normalize www/non-www, strip query strings irrelevant to identity)
2. Title/topic similarity check against existing entries' frontmatter `title:` and `subtitle:` using a token-overlap or character-trigram cosine similarity (no embedding model required — same approach ESP-CLAW uses)
3. If similarity >= 0.85, skip with info message "Resource appears to match existing entry: {path}. Use `--rerun {category}/{name}` to refresh."

Field `similarity_threshold` exposed as a parameter (default 0.85) in the helper script and documented in `batch-mode.md`.

### Measurable signal

Run: `uv run .claude/skills/research-curator/scripts/check_resource_duplicates.py --url https://esp-claw.com/ --against-vault ./research/`. Output JSON includes `matches: [{path: "agent-frameworks/esp-claw.md", similarity: 0.92, reason: "title token overlap"}]` because `agent-frameworks/esp-claw.md` already exists with overlapping title tokens. Re-running with `--url https://github.com/espressif/esp-claw` produces the same match with a similarity score above the threshold. `references/batch-mode.md` Wave Spawning section references the script and shows it being invoked before URL spawn.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Persistent script generation and caching (LLM generates Lua → device persists → executes on subsequent boots without LLM call) | medium | Maps loosely to "skill/agent content generation by an LLM that is then re-used by Claude Code without re-prompting" but no concrete file or mechanism in the local repo presents an obvious target. Would require interviewing whether any current workflow re-invokes the LLM for content that could be cached. Raise to high confidence after confirming an actual workflow that re-prompts the LLM for content already produced. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Streaming JSON parser with 8KB ring buffer | Architectural mismatch — Claude Code agents run in environments with megabytes/gigabytes of memory. The constraint that motivates ring-buffer streaming (400KB SRAM on ESP32) does not exist in any local file under `/home/user/claude_skills/plugins/` or `/home/user/claude_skills/.claude/skills/`. Pattern is incompatible with the local architecture. |
| Event-driven agent architecture with FreeRTOS scheduler | No actionable observable target state. Claude Code agents fundamentally operate on user/orchestrator dispatch, not on async hardware/sensor events. The nearest analog (Claude Code hooks: PreToolUse/PostToolUse/SessionStart/Stop via `settings.json`) is already a first-class event mechanism. Adjacent improvement (behavioral fingerprint tracking on PostToolUse) is already tracked as #1109. |
| Tool schema standardization via MCP | Already implemented — repo extensively uses MCP via `/fastmcp-creator:fastmcp-creator` skill, `/plugin-creator:mcp-integration`, and many active MCP servers (`mcp__plugin_dh_backlog__*`, `mcp__plugin_dh_sam__*`, `mcp__github__*`, `mcp__Ref-local__*`). |
| Lightweight memory injection (summary in system prompt vs full recall via tool) | Already tracked as #1089 — "Add semantic compaction for completed SAM tasks to reduce context window consumption". The ESP-CLAW pattern is a precedent for the same approach already in flight. |
| Hybrid local-remote decision making via MCP bidirectional integration | Already supported — Claude Code agents already mix local tool calls with remote MCP server calls. No actionable gap. |
| Multi-LLM backend support (OpenAI / Anthropic / Bailian / DeepSeek / custom) | Out of scope — Claude Code is Anthropic-first by design; multi-provider abstraction is not a goal of this repo. |

---

## Notes for Reviewers

This file was re-evaluated 2026-05-02 against the gap assessment rules in `research-insight-extractor` skill. The earlier assessment (which produced zero proposals) classified the semantic-deduplication pattern as "no observable gap" without checking research-curator's actual deduplication implementation. Verifying `.claude/skills/research-curator/references/batch-mode.md` line 67 confirmed that local deduplication is URL-string equality only — the ESP-CLAW pattern (paraphrase / similarity match) is genuinely absent and the gap is observable in a specific file with a measurable signal.
