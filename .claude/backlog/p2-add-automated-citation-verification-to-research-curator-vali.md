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
  last_synced: '2026-03-19T02:13:15Z'
---