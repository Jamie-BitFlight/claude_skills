# Content Fidelity Audit: the-rewrite-room Plugin

**Audited**: 2026-02-20
**Plugin**: `plugins/the-rewrite-room/`
**Source files checked**: 6 claims against 6 source files

---

## Check 1: fidelity-rules.md

**Plugin file**: `plugins/the-rewrite-room/skills/the-rewrite-room/references/fidelity-rules.md`
**Source file**: `plugins/summarizer/skills/summarizer/references/fidelity-rules.md`

**Verdict: ADAPTED** — substantial paraphrase with structural changes and content loss

### Evidence

The plugin file's preamble differs from source:

```
SOURCE:  "These rules govern ALL summarization operations in this plugin. They exist to prevent
          the three failure modes observed in AI summarization:"

PLUGIN:  "These rules apply to ALL summarization operations routed through the-rewrite-room.
          They consolidate the rules from the summarizer plugin and the global CLAUDE.md
          summarization rules."
```

Rule 1 heading format differs:

```
SOURCE:  "## Rule 1: Read Before Summarizing"
PLUGIN:  "## Rule 1 — Read Before Summarizing"
```

Rule 1 required behavior — the plugin **drops the WebFetch option**:

```
SOURCE:  "Use WebFetch or mcp__Ref__ref_read_url to read URLs"
PLUGIN:  "Use `mcp__Ref__ref_read_url` to read URLs"
```

Rule 1 adds a mermaid flowchart that does not exist in the source file. The source has no decision flowchart for file size in Rule 1.

Rule 3 — the source uses a markdown **table** to show prohibited transformations. The plugin **removes the table** and rewrites the rule as bullet prose, losing the structured row-by-row presentation. Example omitted from source text is `"7 of 10 items found (3 sources were inaccessible)..."` which the plugin also omits.

Rule 4 — the source table has 5 rows including `"Ambiguous/unclear"`. The plugin omits that row, reducing to 4 rows.

Rule 5 — source has a multi-line prohibited pattern showing "Agent researches 10 items → finds 7..." The plugin condenses this, cutting the first line.

Rule 6 — source: "Every summary MUST include a confidence assessment **in the YAML frontmatter**." Plugin: "Every summary MUST include a confidence assessment." (Drops the "in the YAML frontmatter" qualifier — meaning changed.)

Source Rule 6 includes: "Source is ambiguous (multiple interpretations possible)" and "Source conflicts with other sources" and "Multiple sources agree" in the confidence factors. Plugin omits "Source is ambiguous" and "Source conflicts with other sources" from reduce-confidence list, and omits "Multiple sources agree" from increase-confidence list.

Rule 5 source has 6 rules for orchestrators (including "Do NOT upgrade 'not found' to 'doesn't exist'"). Plugin has only 5, dropping rule 6.

Rule 7 differs structurally:

```
SOURCE:  references template via link: "[Structured Summary](../templates/structured.md)"
PLUGIN:  "Required sections: Summary, What Was Found, What Was NOT Found, Uncertain, Sources"
         (inline enumeration — no link to template)
```

Plugin adds an entirely new section "## Fidelity Validator Trigger Phrases" that has no counterpart in the source file.

**Summary**: Rules are present and recognizable from the source, but the plugin paraphrases, reformats, removes table structure, drops several sub-items from Rules 4, 5, 6, and adds content not in the source (flowchart, trigger phrases section). Content is substantially adapted, not verbatim.

---

## Check 2: registry/validators.yaml — `--file` flag

**Plugin claim** (`plugins/the-rewrite-room/skills/the-rewrite-room/registry/validators.yaml`, line 5):
```yaml
invocation: "uv run {script} --file {target}"
```

**Actual script** (`plugins/gitlab-skill/skills/gitlab-skill/scripts/validate_glfm.py`, line 128-130):
```python
input_group.add_argument("--file", "-f", type=Path, help="Path to markdown file to validate")
```

**Verdict: VERBATIM** — `--file` is the correct flag. The script's argparse definition at line 128 confirms `--file` (with short alias `-f`). The invocation in validators.yaml matches the actual CLI interface exactly.

---

## Check 3: workflows/drift-audit.md — canonical agent path

**Plugin claim** (`plugins/the-rewrite-room/skills/the-rewrite-room/workflows/drift-audit.md`, frontmatter lines 3-4):
```yaml
canonical_agent: doc-drift-auditor
canonical_path: plugins/development-harness/agents/doc-drift-auditor.md
```

**Actual file existence**: Confirmed. `plugins/development-harness/agents/doc-drift-auditor.md` exists.

**Agent frontmatter** (lines 1-7 of that file):
```yaml
---
name: doc-drift-auditor
description: Audits documentation accuracy against actual implementation. Analyzes git
  history to identify when code and documentation diverged, extracts actual features
  from source code, compares against documentation claims. Generates comprehensive
  audit reports categorizing drift (implemented but undocumented, documented but
  unimplemented, outdated documentation, mismatched details). Uses git forensics,
  code analysis, and evidence-based reporting with specific file paths, line numbers,
  and commit SHAs.
model: sonnet
permissionMode: acceptEdits
color: orange
skills: subagent-contract
---
```

**Plugin claim about what the agent does** (drift-audit.md, lines 13-20):
```
Evidence-based comparison of documentation versus code using git forensics.

Detects:
- Implemented features not mentioned in any documentation
- Features documented as existing that are no longer in the codebase
- Stale cross-references pointing to renamed or deleted symbols
- Documentation whose language does not match the actual implementation
```

**Verdict: ADAPTED** — The agent path is correct and the file exists. The description of what the agent does is broadly consistent with the agent's actual description. However, the plugin adds "Stale cross-references pointing to renamed or deleted symbols" which is not explicitly stated in the agent description. The agent description does not mention cross-reference checking. The other three detection items are faithful to the agent's description.

---

## Check 4: routing-rules.yaml trigger keywords vs agent description

**Plugin claim** (`plugins/the-rewrite-room/skills/the-rewrite-room/registry/routing-rules.yaml`, lines 6-18):
```yaml
drift-audit:
  keywords:
    - "out of date"
    - "stale"
    - "diverged"
    - "undocumented"
    - "documented but"
    - "drift"
    - "audit docs"
    - "code changed"
    - "implemented but undocumented"
    - "documented but unimplemented"
    - "docs don't match"
    - "verify documentation"
```

**Actual agent description** (`plugins/development-harness/agents/doc-drift-auditor.md`, line 3):
"Audits documentation accuracy against actual implementation. Analyzes git history to identify when code and documentation diverged, extracts actual features from source code, compares against documentation claims. Generates comprehensive audit reports categorizing drift (implemented but undocumented, documented but unimplemented, outdated documentation, mismatched details). Uses git forensics, code analysis, and evidence-based reporting with specific file paths, line numbers, and commit SHAs."

**Verdict: INVENTED** — The agent description contains no trigger keywords list. There is no "keywords" section in the agent. The plugin's routing-rules.yaml invented a trigger keyword set. However, most keywords are semantically consistent with what the agent does ("diverged", "documented but unimplemented", "implemented but undocumented", "drift" all appear conceptually in the agent description). The keywords themselves were not sourced from any explicit list in the agent file — they were generated by the implementing agent based on the agent's purpose.

The term "out of date" and "stale" do not appear in the agent description at all. "Audit docs" and "code changed" are also inventions. "Verify documentation" does not appear in the agent description.

---

## Check 5: scripts/router.py — YAML loading vs hardcoded logic

**Plugin file**: `plugins/the-rewrite-room/skills/the-rewrite-room/scripts/router.py`

The router.py script:

- Lines 28-29: Defines `ROUTING_RULES_PATH = REGISTRY_DIR / "routing-rules.yaml"` and `WORKFLOWS_PATH = REGISTRY_DIR / "workflows.yaml"`
- Lines 44-51: `_load_routing_rules()` loads from the YAML path using ruamel.yaml, raises Exit(1) if file missing
- Lines 117-118: `classify()` command calls `_load_routing_rules()` and `intent_signals = rules.get("routing", {}).get("intent_signals", {})`
- Lines 91-97: `_get_chain()` reads `chain_rules` from the loaded YAML data
- Lines 151-157: Disambiguation rules read from `rules.get("routing", {}).get("disambiguation", [])` in the loaded YAML

**Verdict: VERBATIM (behavior consistent with YAML)** — The router has no hardcoded keyword lists. All routing logic — keywords, source signals, artifact signals, chain rules, and disambiguation rules — is read dynamically from `routing-rules.yaml`. The script is a pure YAML-driven router with no logic duplicating or contradicting the YAML. The implementation is self-consistent.

---

## Check 6: add-doc-updater-adapter.md claims vs actual SKILL.md

**Plugin claim** (`plugins/the-rewrite-room/skills/the-rewrite-room/workflows/adapters/add-doc-updater-adapter.md`, lines 14-25):

```
This skill orchestrates a 5-phase workflow that ends with the sync script integrated
into the target skill's SKILL.md.

## Native Output Contract

The `add-doc-updater` skill does not produce a STATUS block. It produces:

1. A Python sync script at a path inside the target skill's `scripts/` directory
2. A reference to that script added to the target SKILL.md execution protocol
3. Phase completion output via sub-agent STATUS/BLOCKED blocks
```

**Actual SKILL.md** (`plugins/plugin-creator/skills/add-doc-updater/SKILL.md`):

The actual skill has phases labeled 0-5 (Phase 0 through Phase 5), making it a **6-phase** workflow (0, 1, 2, 3, 4, 5), not a 5-phase workflow as claimed.

Phase 0 collects variables, Phase 1 implements, Phase 2 reviews, Phase 3 runs quality gates, Phase 4 tests, Phase 5 integrates. The adapter says "5-phase workflow" — this is wrong.

**Claimed outputs match actual**: The actual SKILL.md confirms (Phase 5, lines 265-316):
- Phase 5a updates target SKILL.md Execution Protocol section
- Phase 5b updates .gitignore
- Phase 5c runs integration test

The adapter's claim about outputs (sync script, SKILL.md reference, STATUS/BLOCKED blocks) is consistent with what the SKILL.md actually does — sub-agents return STATUS/BLOCKED blocks per Phase 1's delegation to `@python-cli-architect`.

The adapter's STATUS block template:
```
SUMMARY: Documentation sync pipeline added to {skill-name}. Sync script created at {script-path}.
ARTIFACTS:
  - {skill-path}/scripts/{sync-script-name}.py
  - {skill-path}/SKILL.md (updated with execution protocol)
```

This is consistent with the actual SKILL.md Phase 5 which creates `scripts/update-{LOCAL_DOC_DIR}-docs.py` and updates SKILL.md.

**Verdict: MISMATCH (partial)** — The phase count is wrong (5-phase claimed, 6-phase actual including Phase 0). The output artifact description is broadly accurate. The STATUS/BLOCKED block structure is plausible but not explicitly specified in the source SKILL.md (which does not define a normalized STATUS block — the adapter invented this normalization layer, which is its stated purpose). The core mismatch is the phase count.

---

## Summary

| Check | Subject | Verdict | Reliability |
|---|---|---|---|
| 1 | fidelity-rules.md content | ADAPTED | Partially reliable — rules present but paraphrased, items dropped, content added |
| 2 | validate_glfm.py `--file` flag | VERBATIM | Reliable — `--file` confirmed at line 128 of actual script |
| 3 | doc-drift-auditor path and description | ADAPTED | Reliable — path correct, description mostly accurate, one addition unsupported |
| 4 | routing-rules.yaml trigger keywords | INVENTED | Unreliable — no keyword list exists in agent; agent has no triggers section |
| 5 | router.py YAML-driven logic | VERBATIM | Reliable — script correctly reads routing-rules.yaml dynamically, no hardcoding |
| 6 | add-doc-updater adapter phase count | MISMATCH | Partially unreliable — 5-phase claimed, 6-phase actual (Phase 0 through 5) |

### Reliability Score

- **Verbatim / directly verified**: 2 of 6 checks (Checks 2, 5)
- **Adapted (mostly accurate, some loss or addition)**: 2 of 6 checks (Checks 1, 3)
- **Invented (no source basis)**: 1 of 6 checks (Check 4)
- **Mismatch (directly contradicts source)**: 1 of 6 checks (Check 6)

**Overall**: 2/6 (33%) verbatim. 4/6 (67%) reliable enough to use with caution. 2/6 (33%) have material errors requiring correction before use.

### Critical Findings

1. **Check 4 (keywords)**: The trigger keyword list in `routing-rules.yaml` was invented without any source. The agent has no triggers section. This is low-risk functionally (keywords are semantically appropriate) but represents fabricated content.

2. **Check 6 (phase count)**: The adapter claims a "5-phase workflow" but the actual `add-doc-updater` skill has 6 phases (Phase 0 through Phase 5). Any documentation or agent that reads this adapter and assumes 5 phases will misunderstand the workflow.

3. **Check 1 (fidelity rules)**: Rule 6 drops the "in the YAML frontmatter" qualifier, changing the meaning of where confidence must be stated. Rule 5 drops the sixth orchestrator rule. Rule 4 drops the "Ambiguous/unclear" row. These are content losses from the source.
