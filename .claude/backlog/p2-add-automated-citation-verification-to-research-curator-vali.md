---
name: Add automated citation verification to research-curator validate mode
description: "**Current state**: The research-curator `--validate` mode checks structural issues (missing required fields, broken links, malformed frontmatter) via `validate_research.py`. It does not verify that cited sources actually exist or are relevant. Citations in research entries (URLs, arXiv IDs, DOI references) are taken at face value. File: `.claude/skills/research-curator/SKILL.md` (validate mode section) and `.claude/skills/research-curator/scripts/validate_research.py`.\n\n**Target state**: The `--validate` mode includes a citation verification layer that checks: (1) URL reachability (HTTP HEAD request, report non-2xx status), (2) arXiv ID format validation and optional API lookup, (3) DOI resolution via CrossRef/DataCite API. Hallucinated or dead references are flagged as warning-severity issues in the validator JSON output. A new `--verify-citations` flag enables this layer (off by default to avoid network dependency in CI).\n\n**Measurable signal**: Run `uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md` -- output includes a `citation_verification` section with per-URL status (reachable/unreachable/invalid-format). At least one research entry with a fabricated URL produces a warning-severity finding."
metadata:
  topic: add-automated-citation-verification-to-research-curator-vali
  source: 'Research entry: ./research/agent-frameworks/AutoResearchClaw.md -- pattern: 4-layer citation verification'
  added: '2026-03-19'
  priority: P2
  type: Feature
  status: open
  issue: '#845'
  last_synced: '2026-03-19T02:20:14Z'
  groomed: '2026-03-19'
---

## RT-ICA

<div><sub>2026-03-19T02:20:14Z</sub>

RT-ICA Snapshot: Add automated citation verification to research-curator validate mode
Goal: Add `--verify-citations` flag to `validate_research.py` that checks URL reachability, arXiv ID format, and DOI resolution, flagging dead/hallucinated references as warning-severity issues in JSON output.

Conditions:
1. `validate_research.py` CLI interface, Issue TypedDict, JSON output schema | Status: DERIVABLE
2. Citation formats in research entries (URL/arXiv/DOI patterns in .md files) | Status: DERIVABLE
3. CrossRef/DataCite API endpoints and response format | Status: DERIVABLE
4. arXiv ID format spec (`\d{4}\.\d{4,5}(v\d+)?`) | Status: AVAILABLE
5. HTTP library in script dependencies (currently `typer` only; new dep needed) | Status: DERIVABLE
6. `--verify-citations` flag integration with existing `--json` and validate workflow | Status: DERIVABLE
7. Warning-severity issues are reported but not auto-fixed (from SKILL.md spec) | Status: AVAILABLE

AVAILABLE count: 2
DERIVABLE count: 5
MISSING count: 0
</div>