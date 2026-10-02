# Improvement Proposals: HashiCorp Agent Skills

**Research entry**: ./research/skill-generation-tools/hashicorp-agent-skills.md
**Generated**: 2026-10-02
**Patterns assessed**: 6
**Backlog items created**: 0 — creation of the one qualifying item was attempted and failed (see Improvement 1)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Skill lifecycle state — record whether each skill is active, deprecated, or retired

**Source pattern**: "Skill Registration: Each skill is a SKILL.md frontmatter directory containing: Required fields: `name` (matching directory name), `description`, `metadata.lifecycle-status`. Supported lifecycle states: `active`, `deprecation-candidate`, `deprecated`, `retired`" (Technical Architecture → Skill Registration); "Lifecycle Governance: All 20 skills marked as `active`" (Key Features → Distribution and Cross-Platform Support). Checked against the primary source on 2026-10-02: `https://raw.githubusercontent.com/hashicorp/agent-skills/main/AGENTS.md` (Skill requirements section states both rules verbatim) and `plugins/terraform/skills/terraform-style-guide/SKILL.md` in that repository (frontmatter `metadata:` / `lifecycle-status: active`).
**Local system**: `plugins/plugin-creator/skills/agentskills/references/specification.md` (Metadata Field section), `plugins/plugin-creator/skills/audit-skill-lifecycle/SKILL.md`
**Absence evidence**: `git grep -il "lifecycle-status\|lifecycle_status" -- plugins/ .claude/ scripts/ docs/` -> 2 matches, both about backlog/work-ledger entry lifecycle (`plugins/development-harness/graphify-out/graph.json`, `plugins/development-harness/tests/test_dh_paths_integration.py:698`), none about skills; `git grep -il "deprecation-candidate"` -> 0 matches; `git grep -n -i "remov\(e\|ing\) a skill\|sunset\|skill.*deprecat\|deprecat.*skill" -- CONTRIBUTING.md docs/ plugins/plugin-creator/ rules/ ARCHITECTURE.md` -> only notes that plugin *commands* are deprecated (`plugins/plugin-creator/skills/plugin-creator/SKILL.md:517`, `plugins/plugin-creator/scripts/create_plugin.py:15`)
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — `mcp__plugin_dh_backlog__backlog_add` returned `GraphQL is unavailable in this environment` (retryable: false); the same error came back from `backlog_list`. Qualifies as P1 (High confidence x Medium impact) and needs creating once the backlog server is reachable. A REST search of all repository issue titles and bodies (2,961 issues, `state=all`) found no existing item for skill lifecycle state; the body matches for "lifecycle status/state" (#398, #426, #714, #1944, #2144, #2415, #3192, #3362, #3901) are about backlog/task state.

### Current state

The portable Agent Skills spec allows arbitrary string keys under `metadata`
(`plugins/plugin-creator/skills/agentskills/references/specification.md`, "Metadata Field"), but no
convention in this repository uses it for lifecycle state, and no skill records one.
`plugins/plugin-creator/skills/audit-skill-lifecycle/SKILL.md` audits call-graph coherence
(circular loads, contradictions, duplicated datasets); it does not read or record whether a skill
is maintained or superseded.

Same-named skills currently exist in two locations with divergent content, and nothing records
which copy is authoritative:

- `.claude/skills/evaluate-sdlc-layers/SKILL.md` vs `plugins/development-harness/skills/evaluate-sdlc-layers/SKILL.md` (`diff -q` -> differ)
- `.claude/skills/fact-check/SKILL.md` vs `plugins/development-harness/skills/fact-check/SKILL.md` (`diff -q` -> differ)
- `.claude/commands/write-to-skill-file.md` vs `.claude/commands/write-to-skill-file-original.md` (137 diff lines)

Both members of each pair are offered to the model as available skills in this session's listing.
An agent picking one has no recorded signal of which is maintained.

### Target state

- A documented convention for `metadata.lifecycle-status` in SKILL.md frontmatter with the four
  states `active`, `deprecation-candidate`, `deprecated`, `retired`, and what each obliges (for
  example, `deprecated` names its replacement), placed in the skill-authoring guidance under
  `plugins/plugin-creator/skills/skill-creator/` and referenced from `CONTRIBUTING.md`.
- A validator (pre-commit hook or test) that rejects an unknown lifecycle value and reports skills
  that carry none.
- Each same-named pair above resolved to a single `active` copy, with any retained copy marked
  non-active.

### Measurable signal

- `git grep -l "lifecycle-status:" -- '*/SKILL.md' | wc -l` equals the number of in-scope tracked
  `SKILL.md` files (278 tracked `SKILL.md` files on 2026-10-02 per `git ls-files | grep -E "SKILL.md$" | wc -l`).
- Setting `lifecycle-status: bogus` in any SKILL.md makes the validator exit non-zero.
- Each pair listed under Current state has at most one copy with `lifecycle-status: active`.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Supported-models matrix with a re-evaluation trigger (Limitations and Caveats → "Model support baseline"; HashiCorp `AGENTS.md`: "Review or reevaluate a Skill whenever the Skill changes or the supported model matrix changes") | low | The pattern sits in the entry's Limitations section, not its Relevance section. `rules/model-selection.md` exists locally and governs model assignment for dispatched agents; whether this repo needs a per-skill supported-model matrix with a re-evaluation trigger requires reading that rule and the skill evaluation tooling (`plugins/plugin-creator/skills/evaluate-and-tighten-skills/`) to establish a concrete gap, which was not done here. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Claude Code / Codex manifest alignment (Limitations: "plugin manifests ... are hand-maintained ... automated alignment is not documented") | Local system is stronger: `scripts/sync_codex_plugin_manifests.py` generates `.codex-plugin/plugin.json` from Claude metadata and has a `--check` mode (documented in `docs/cross-harness-smoke-tests.md:59`, tested by `tests/test_sync_codex_plugin_manifests.py`); 28 tracked `.codex-plugin/plugin.json` files and `.agents/plugins/marketplace.json` exist. |
| Marketplace metadata versioning (Relevance → Applications, item 3) | The entry itself states HashiCorp's versioning matches claude_skills' pattern. Local is stronger: `docs/marketplace-versioning.md` describes CI-assigned patch bumps and the `agent-marketplace-versioner-check` hook that fails on manifest/marketplace drift for both `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`. |
| Product-scoped skill organization (Relevance → Absence Anchors: "product bundle", "product plugin" 0 matches) | The zero matches are terminological. This repository already groups skills into domain plugins under `plugins/<name>/`, each with its own Claude and Codex manifests, which is the structure the entry describes for `plugins/terraform/` and `plugins/packer/`. No observable gap. |
| Cite HashiCorp as a case study in `plugins/plugin-creator/skills/agentskills/SKILL.md` and `plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md` (Relevance → Applications, items 1 and 2) | Too abstract: adding an external example to reference docs closes no failure mode and has no observable before/after behavior. The one concrete mechanism behind it (lifecycle governance) is Improvement 1. |
