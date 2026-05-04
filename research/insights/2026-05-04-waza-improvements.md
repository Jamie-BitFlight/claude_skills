# Improvement Proposals: Waza — Engineering Habits as Claude Skills

**Research entry**: ./research/skill-generation-tools/waza.md
**Generated**: 2026-05-04
**Patterns assessed**: 6
**Backlog items created**: 3 (issues: #2124, #2125, #2126)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Marketplace ↔ skill directory cross-reference validation

**Source pattern**: From research entry, "Verification and Validation" — `./scripts/verify-skills.sh` "enforces ... Every marketplace entry has a matching `skills/*/SKILL.md` directory" and "`skills/RESOLVER.md` routing table references only existing skills". Verified directly against `.worktrees/waza/AGENTS.md` Verification section: "Marketplace, resolver, or root dispatcher changes: run `./scripts/verify-skills.sh` and confirm every marketplace source points at an existing skill directory."
**Local system**: `/home/user/claude_skills/.claude-plugin/marketplace.json` (30 plugin entries) and `plugins/*/` directories; current validator is `uvx skilllint@latest` which checks individual skill structure but does not cross-reference marketplace entries against actual plugin directories.
**Confidence**: High
**Impact**: High
**Backlog**: #2124 created

### Current state

`/home/user/claude_skills/.claude-plugin/marketplace.json` lists 30 plugins as `{ "name": "...", "source": "./plugins/..." }` entries. Plugin auto-sync is handled by `plugins/plugin-creator/scripts/auto_sync_manifests.py`, which updates plugin component arrays and version fields on commit. There is no validator that walks `marketplace.json` plugin entries, resolves each `source` path, and verifies the referenced directory exists with a valid `.claude-plugin/plugin.json`. A renamed/deleted plugin directory results in a stale marketplace entry that passes lint but breaks installation. Evidence: no script in `/home/user/claude_skills/scripts/` or `plugins/plugin-creator/scripts/` references `marketplace.json` cross-validation; `grep -r "marketplace.*skills\|skills.*marketplace"` over `plugin-creator/scripts/` returns zero hits.

### Target state

A validator script `scripts/verify_marketplace_consistency.py` runs in pre-commit and CI. For every entry in `.claude-plugin/marketplace.json`'s `plugins[]` array: (1) resolves `source` relative to repo root; (2) confirms the directory exists; (3) confirms `<source>/.claude-plugin/plugin.json` exists and is valid JSON; (4) confirms the `name` field in `marketplace.json` matches the `name` in the plugin's own `plugin.json`. Exits non-zero on any mismatch with a list of broken entries.

### Measurable signal

Run: `uv run scripts/verify_marketplace_consistency.py` — exit code 0 with no output when consistent. Manually delete a plugin directory and re-run — exit code is non-zero with an error like `marketplace entry 'agent-orchestration' references missing directory ./plugins/agent-orchestration`. Pre-commit hook entry added to `.pre-commit-config.yaml` invoking the script. CI workflow `quality-gate-audit.yml` includes a step that runs the script.

---

## Improvement 2: "Not for" exclusion section in skill frontmatter description

**Source pattern**: From research entry "Skill Design Principles" (item 4): "Explicit 'Not for' sections — Each skill states what it doesn't do, reducing ambiguity about when to use which skill." Verified directly in `.worktrees/waza/skills/check/SKILL.md` line 3: `description: "... Not for exploring ideas or debugging."` and `.worktrees/waza/AGENTS.md`: "Create or update `skills/<name>/SKILL.md`; keep the description concrete, triggerable, and include a `Not for ...` exclusion."
**Local system**: `/home/user/claude_skills/plugins/plugin-creator/skills/skill-creator/SKILL.md` (Step 5 frontmatter guidance) and `/home/user/claude_skills/plugins/plugin-creator/skills/write-frontmatter-description/`.
**Confidence**: High
**Impact**: Medium
**Backlog**: #2125 created

### Current state

`plugins/plugin-creator/skills/skill-creator/SKILL.md` Step 5 §"Frontmatter" instructs authors on how to write `description` (lines ~471-477): "Include both what the Skill does and specific triggers/contexts for when to use it. Include all 'when to use' information here." There is no guidance to include an explicit exclusion clause naming what the skill is NOT for. Spot-check of local skills (e.g., `plugins/development-harness/skills/discovery/SKILL.md` line 3) shows descriptions list positive triggers only, no negative scope. With ~280 skills and overlapping triggers (e.g., `discovery` vs `find-cause` vs `rt-ica`), Claude has no explicit signal to disambiguate when multiple descriptions could match.

### Target state

`plugin-creator/skills/skill-creator/SKILL.md` Step 5 §"Frontmatter" gains a required clause: "End the description with a `Not for: <comma-separated list>` clause naming workflows this skill explicitly excludes." `plugin-creator/skills/write-frontmatter-description/SKILL.md` is updated with the same rule and an example. `skilllint` adds a new informational rule (e.g., `SK0XX-not-for-clause-missing`) that warns when a skill description does not contain a `Not for` clause — INFO-level only, not blocking.

### Measurable signal

Read `plugins/plugin-creator/skills/skill-creator/SKILL.md` — the Step 5 §"Frontmatter" section contains the literal string `Not for:` requirement and an example description ending with a `Not for ...` clause. Read `plugins/plugin-creator/skills/write-frontmatter-description/SKILL.md` — same rule present. Run `uvx skilllint@latest check plugins/development-harness/skills/discovery/` — output includes informational notice naming the missing `Not for` clause.

---

## Improvement 3: Routing table validation for skill name → trigger consistency

**Source pattern**: From research entry "Verification and Validation": "`skills/RESOLVER.md` routing table references only existing skills". Verified in `.worktrees/waza/skills/RESOLVER.md` (60 lines of trigger → SKILL.md path tables) and `.worktrees/waza/AGENTS.md`: "Keep `skills/RESOLVER.md` in sync when a skill description, trigger, or scope changes."
**Local system**: `/home/user/claude_skills/plugins/development-harness/skills/development-harness/SKILL.md` and per-plugin `CLAUDE.md` files document skill routing (e.g., the dh CLAUDE.md "Skills Overview" section lists 30+ `/dh:*` skills with one-line descriptions).
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the routing-table-as-validation-target pattern depends on whether this repo wants to formalize per-plugin SKILL routing tables (Waza has one resolver for 8 skills; this repo has 30 plugins with 200+ skills, so the equivalent design choice is non-obvious).

### Current state

Each plugin's `CLAUDE.md` lists its skills in a "Skills Overview" section as bullet points with short descriptions (e.g., `plugins/development-harness/CLAUDE.md` lines listing `/dh:add-new-feature`, `/dh:implement-feature`, etc.). These lists are maintained by hand. There is no validator that confirms every skill listed in `CLAUDE.md` exists as a directory under `plugins/<name>/skills/`, and no validator that confirms every skill directory under `skills/` is referenced in `CLAUDE.md`. Drift is possible in either direction.

### Target state

A validator that, for each plugin with a `CLAUDE.md`, parses the "Skills Overview" / Skills inventory section and (1) resolves each `/<plugin>:<skill>` reference to a directory path; (2) reports references with no matching skill directory; (3) reports skill directories not referenced in `CLAUDE.md`.

### Measurable signal

Add a script + pre-commit hook. Adding a fake skill reference like `/dh:nonexistent-skill` to `plugins/development-harness/CLAUDE.md` causes the validator to fail with the stale reference name. Removing a referenced skill's directory causes the validator to fail with the orphaned reference.

**Deferral reason**: This repo's per-plugin CLAUDE.md design differs from Waza's single RESOLVER.md, and the marginal value over `skilllint`'s existing component-presence checks needs evaluation. Recommend revisiting after Improvement 1 (marketplace cross-reference) lands to evaluate whether the same machinery can be extended to the per-plugin CLAUDE.md case.

---

## Improvement 4: Mandatory shared output marker enforced by linter

**Source pattern**: From research entry "Verification and Validation": "Shared output marker `🥷` present in every skill". Verified in `.worktrees/waza/skills/check/SKILL.md` line 11: "Prefix your first line with 🥷 inline, not as its own paragraph" and `.worktrees/waza/skills/RESOLVER.md` line 5: "所有技能都沿用同一个输出约定：首行内联带上 `🥷` ... `verify-skills.sh` 也会校验它."
**Local system**: This repo's CLAUDE.md (`/home/user/claude_skills/.claude/CLAUDE.md`) defines "Response style: Concise, precise, direct answer only" but no per-skill output marker convention exists.
**Confidence**: High
**Impact**: Low
**Backlog**: Deferred — impact too narrow to justify a backlog item: per-skill output markers are a Waza branding choice; this repo's convention is "concise direct answer only" which is functionally equivalent for the AI consumer. Adopting an emoji marker would conflict with `.claude/CLAUDE.md` rule "Only use emojis if the user explicitly requests it. Avoid using emojis in all communication unless asked." (Tone and style section).

### Current state

Per the cited CLAUDE.md rule, this repo explicitly avoids emoji in assistant output. Waza's marker pattern is a cosmetic identification for users who want to see "this came from a Waza skill" — incompatible with this repo's no-emoji rule.

### Target state

No change. The Waza pattern is rejected as architecturally incompatible.

### Measurable signal

N/A.

---

## Improvement 5: Multi-mode skill architecture — explicit mode branching with disambiguation rules

**Source pattern**: From research entry "Skill Modes and Branching": `/think` skill has three independent modes (Standard/Lightweight/Evaluation); `/check` skill has three parallel modes (Code review/Ship-Release/Triage). Verified in `.worktrees/waza/skills/check/SKILL.md` Triage Mode section (line 34) and Ship/Release Follow-through section (line 51). Disambiguation rules in `.worktrees/waza/skills/RESOLVER.md` lines 46-55 (numbered rules 1-9 explaining when each mode wins).
**Local system**: `/home/user/claude_skills/plugins/plugin-creator/skills/skill-creator/SKILL.md` (Step 5 body guidance) and `plugins/plugin-creator/skills/refactor-skill/SKILL.md`.
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: this repo's existing pattern is "split when domains diverge" (refactor-skill pattern) — Waza's "branch within one skill via labelled modes" is the opposite design choice. Whether multi-mode-within-one-skill is a net improvement depends on the trade-off between description length budget (1024 chars) and the overhead of cross-skill orchestration. Needs experiment to validate.

### Current state

`plugins/plugin-creator/skills/refactor-skill/SKILL.md` is the canonical guidance for splitting oversized skills: when a skill covers multiple domains, split into separate skills (`SKILL_SPLIT` task type). There is no documented pattern for the alternative — keeping one skill that branches into named modes via clear disambiguation rules. The `skill-creator` Step 5 body template encourages flowcharts but does not give a "multi-mode within one skill" template.

### Target state

`skill-creator/references/workflows.md` gains a section "Multi-mode skill pattern" with: (1) when to use it (mutually exclusive workflows that share project-context extraction or other expensive setup steps); (2) required components (numbered disambiguation rules between modes, explicit "Activate when..." clause per mode); (3) example template based on Waza's `/check` (Code review / Ship / Triage).

### Measurable signal

Read `plugins/plugin-creator/skills/skill-creator/references/workflows.md` — section "Multi-mode skill pattern" present, contains a numbered disambiguation rule list and an example template. At least one local skill (candidates: `dh:work-backlog-item`, `dh:dispatch`) has been audited against the new template and either restructured or annotated with rationale.

**Deferral reason**: This is a pattern recommendation, not a bug fix. Add to backlog only after one experimental application to a candidate skill to measure whether description-length and routing accuracy actually improve.

---

## Improvement 6: Scoped smoke tests with mock-environment validation for installer scripts

**Source pattern**: From research entry "Verification and Validation": Makefile smoke targets — `smoke-statusline-installer: Tests installer with mock environment (HOME, PATH override)`, `smoke-english-coaching-installer: Tests coaching rule install idempotence`, `smoke-package: Validates generated ZIP has exactly one root SKILL.md`, `smoke-verify-skills: Tests 6 validation edge cases`. Verified in `.worktrees/waza/AGENTS.md` Commands section: `make test`, `make package`, `./scripts/verify-skills.sh`.
**Local system**: `/home/user/claude_skills/scripts/` (9 maintenance scripts including `check_symlinks.py`, `repair_symlinks.py`, `process-research-integration.py`) and `plugins/plugin-creator/scripts/` (init_skill, package_skill, etc.). Pre-commit hooks via `.pre-commit-config.yaml` and `prek` runner. CI workflows at `.github/workflows/`.
**Confidence**: High
**Impact**: Medium
**Backlog**: #2126 created

### Current state

Pre-commit hooks run linters (`ruff`, `ty`, `markdownlint`, `auto_sync_manifests.py`). CI workflow `code-quality.yml` runs the same. No script in `/home/user/claude_skills/scripts/` or under any plugin runs an end-to-end smoke test of installer or scaffolder scripts (e.g., `init_skill.py`, `package_skill.py`) against a mock `HOME`/`PATH` environment to verify idempotence and edge cases. `init_skill.py` validates inputs but is never executed in CI with a tmpdir target. `package_skill.py` is never executed against a known-good skill directory in CI to validate ZIP structure. Failure mode: a regression that breaks `init_skill.py` (e.g., wrong path resolution, missing example file) is only caught when a developer runs it manually.

### Target state

A `Makefile` (or equivalent `scripts/smoke_tests.py`) at repo root with targets:

- `smoke-init-skill`: runs `init_skill.py demo-skill --path $(mktemp -d)` and asserts the generated tree matches expected layout (SKILL.md exists, frontmatter parses, `scripts/`, `references/`, `assets/` present, example files exist).
- `smoke-package-skill`: runs `package_skill.py` against a known-good fixture skill in `tests/fixtures/` and asserts the resulting `.skill` ZIP contains exactly the expected entries.
- `smoke-validate-skills`: runs `uvx skilllint@latest check` against a corpus of intentionally-broken skill fixtures and asserts each emits its expected error code.

CI workflow `code-quality.yml` invokes these targets after lint passes.

### Measurable signal

Run `make smoke-init-skill` — exit code 0, output ends with `OK: skill scaffolded with N expected files`. Run `make smoke-package-skill` — exit code 0, output names the produced ZIP and lists its expected entries. Intentionally break `init_skill.py` (e.g., remove a line writing `references/`) — `make smoke-init-skill` exits non-zero with a specific assertion message naming the missing path. CI workflow `.github/workflows/code-quality.yml` contains an explicit `make smoke-*` step.

---

## Improvement 7: Source-root SKILL.md / dispatcher anti-pattern check

**Source pattern**: From research entry "Distribution and Installation": "Release: v3.12.2 (May 4, 2026) restores default `npx skills add tw93/Waza` behavior for direct skill discovery and removes source-root `SKILL.md` that caused discovery to halt at `/waza`." And "Distribution Packaging" — source has no root `SKILL.md`; Claude Desktop ZIP contains a single generated root `SKILL.md` for distribution only. Verified in `.worktrees/waza/AGENTS.md` Distribution Rules: "Do not add a source-root `SKILL.md`; it prevents nested skill discovery."
**Local system**: This repo's structure — no `SKILL.md` exists at repo root, but `plugins/<name>/` directories use the documented Claude Code plugin structure. Existing rule in `/home/user/claude_skills/.claude/CLAUDE.md`: "All skill directories must sit directly under `skills/` — one level deep only. Do not create grouping subdirectories" — already addresses the analogous "subdirectory namespacing" anti-pattern.
**Confidence**: High
**Impact**: Low
**Backlog**: Skipped — already covered by the existing CLAUDE.md rule "Subdirectory Namespaces — Skills Do NOT Support This" which addresses the same class of discovery-halting structural error. The Waza-specific "source-root SKILL.md" variant does not occur in this repo because plugins are the unit of distribution, not a top-level SKILL.md. No action required.

### Current state

CLAUDE.md rule "Subdirectory Namespaces — Skills Do NOT Support This" already prohibits the analogous pattern. No `SKILL.md` exists at any plugin root or repo root. `.claude/skills/` correctly contains skills directly (no nesting).

### Target state

No change. Existing rule is sufficient.

### Measurable signal

N/A — already enforced.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Routing table validation (Improvement 3) | Medium | Per-plugin CLAUDE.md design diverges from Waza's single RESOLVER.md; needs scoping decision before backlogging |
| Multi-mode skill architecture (Improvement 5) | Medium | Pattern recommendation only — needs one experimental application to validate net benefit before backlogging |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Shared output marker `🥷` (Improvement 4) | Architecturally incompatible — repo CLAUDE.md prohibits emoji in assistant output |
| Source-root SKILL.md anti-pattern (Improvement 7) | Already covered by existing CLAUDE.md rule "Subdirectory Namespaces — Skills Do NOT Support This" |
