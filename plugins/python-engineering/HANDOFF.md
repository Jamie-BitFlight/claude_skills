# Handoff: python-engineering Plugin Redesign

## Task

Redesign the `python3-development` plugin (30+ overlapping skills, 3 redundant routers) into a coherent `python-engineering` plugin following the architecture plan at `plugins/python3-development/python_plugin_redesign.md` (1171 lines, 7 sections).

## What's Done

The new plugin exists at `plugins/python-engineering/` with **153 files** and **68 staged git additions**. All structural work is complete:

- **18 SKILL.md files** (all under 123 lines, all have valid YAML frontmatter)
- **5 agents** (cli-architect, pytest-architect, code-reviewer, cli-design-spec, semantic-code-search)
- **6 scripts** (all `.sh` files are executable)
- **3 asset templates** (pyproject.toml.j2, pre-commit-config.yaml, boundary_module_example.py)
- **~100 reference files** migrated from the old plugin into skill-specific `references/` dirs
- **plugin.json** (version 9.1.0), **validator.json**, **CLAUDE.md**, **README.md**

### Architecture (implemented)

| Layer | Skills | Invocation |
|-------|--------|------------|
| Automatic router | `python3-core` | `user-invocable: false` (stays in context, auto-invoked) |
| Specialists (7) | `python3-typing`, `python3-testing`, `python3-cli`, `python3-web`, `python3-data`, `python3-stdlib-only`, `python3-tools` | `user-invocable: false` (auto-loaded by router) |
| Manual TDD | `python3-tdd` | `user-invocable: true`, `argument-hint: '<feature-description>'` |
| Manual entrypoints (5) | `orchestrate`, `review`, `lint`, `cleanup`, `debug` | `disable-model-invocation: true` (user-triggered only) |
| Backward-compat (4) | `modernpython`, `shebangpython`, `stinkysnake`, `snakepolish` | `user-invocable: true` |

### Reference file counts per skill

| Skill | Ref files | Source |
|-------|-----------|--------|
| python3-core | 11 | Migrated from old plugin |
| python3-cli | 28 | Migrated from old typer/, rich/, typer-and-rich/, textual/ skills |
| python3-tools | 44 | Migrated from old uv/, ty/, pre-commit/, hatchling/ skills |
| python3-typing | 11 | Mix of migrated (mypy-docs, type-patterns, type-safety-mypy, modernization-guide) and stubs |
| python3-testing | 3 | Mix of migrated (agent-prompts, plan-templates) and stub (testing-standards) |
| python3-stdlib-only | 3 | Migrated from old stdlib-scripting skill |
| python3-data | 0 | **Empty — no references migrated** |
| python3-web | 0 | **Empty — no references migrated** |

---

## What Remains (5 tasks)

### Task 1: Fix 11 Broken SKILL.md References

Each SKILL.md's `## References` section points to filenames that don't match the actual migrated files.

**python3-cli/SKILL.md** (3 broken):

| Broken ref | Actual files to reference |
|------------|--------------------------|
| `references/typer-patterns.md` | `typer-app-and-commands.md`, `typer-parameters.md`, `typer-parameter-types.md`, `typer-advanced-patterns.md`, `typer-subcommands.md`, `typer-testing.md` |
| `references/rich-patterns.md` | `rich-console-and-markup.md`, `rich-renderables.md`, `rich-text-and-syntax.md`, `rich-advanced-patterns.md`, `rich-progress-and-live.md`, `rich-logging-and-tracebacks.md` |
| `references/typer-rich-integration.md` | `typer-rich-non-tty-patterns.md`, `typer-rich-tables.md`, `typer-rich-exception-handling.md`, `typer-rich-testing-patterns.md` |

**python3-data/SKILL.md** (2 broken):

| Broken ref | Fix |
|------------|-----|
| `references/design-standards.md` | Change to `../../references/design-standards.md` (plugin-level file) |
| `references/pandas-patterns.md` | Remove (file doesn't exist anywhere) OR create it |

**python3-web/SKILL.md** (2 broken):

| Broken ref | Fix |
|------------|-----|
| `references/design-standards.md` | Change to `../../references/design-standards.md` |
| `references/web-patterns.md` | Remove (file doesn't exist anywhere) OR create it |

**python3-stdlib-only/SKILL.md** (2 broken):

| Broken ref | Fix |
|------------|-----|
| `references/compatibility-lanes.md` | Actual file: `command-execution.md`, `type-safety-patterns.md`, `typing-strategy.md` |
| `references/tooling-defaults.md` | This file exists in `python3-tools/references/` not here — either cross-ref or remove |

**python3-testing/SKILL.md** (2 broken):

| Broken ref | Fix |
|------------|-----|
| `references/async-testing.md` | Remove (doesn't exist) OR create it |
| `references/mutation-testing.md` | Remove (doesn't exist) OR create it |

### Task 2: Update Stale Version Pins

| File | Line | Current | Should be |
|------|------|---------|-----------|
| `assets/templates/pyproject.toml.j2` | ~27 | `ty>=0.0.0a1` | `ty>=0.0.26` |
| `assets/templates/pre-commit-config.yaml` | ~10 | `rev: 0.0.0-alpha.11` (ty) | Current ty release tag (verify on PyPI) |
| `assets/templates/pre-commit-config.yaml` | ~3 | `rev: v0.9.0` (ruff) | Verify current ruff release |

### Task 3: Review SKILL.md Body Content Against Migrated References

**Critical quality issue**: SKILL.md bodies were written from training data memory, not from the actual verified content in the old plugin's reference files. Each needs review.

Priority order:

1. **python3-cli/SKILL.md** — Verify the Rich width measurement pattern (`Measurement.get(console, options, renderable)` → measure-first-render-second) matches what's in `typer-rich-non-tty-patterns.md` and `assets/typer_examples/console_containers_no_wrap.py`
2. **python3-core/SKILL.md** — Verify typing policy section matches migrated `python3-standards.md`
3. **python3-typing/SKILL.md** — Verify boundary patterns match `type-safety-mypy.md` and `type-patterns.md`
4. **python3-tools/SKILL.md** — Verify tool config patterns match `ty/`, `uv/`, `hatchling/` references
5. **python3-testing/SKILL.md** — Verify test patterns match `agent-prompts.md` and `plan-templates.md`
6. **python3-stdlib-only/SKILL.md** — Verify stdlib patterns match `command-execution.md`, `type-safety-patterns.md`, `typing-strategy.md`
7. **Stub reference files** that need content review (written from memory, not migrated):
   - `python3-core/references/typing-matrix.md`
   - `python3-typing/references/typing-policy.md`
   - `python3-typing/references/pydantic-boundaries.md`
   - `python3-typing/references/hypothesis-boundaries.md`
   - `python3-testing/references/testing-standards.md`
   - `python3-tools/references/tooling-defaults.md`
   - `python3-tools/references/compatibility-lanes.md`
   - `references/design-standards.md` (plugin-level)

### Task 4: Run Validation

```bash
# Run the plugin's own validation script
bash plugins/python-engineering/scripts/validate-manifest.sh plugins/python-engineering

# Run broken reference check (should return zero after Task 1)
for skill_md in plugins/python-engineering/skills/*/SKILL.md; do
  grep -oP 'references/[^\s\)]+\.md' "$skill_md" | while read ref; do
    [ ! -f "$(dirname "$skill_md")/$ref" ] && echo "BROKEN: $(basename $(dirname "$skill_md")) -> $ref"
  done
done

# Run skilllint if available
uvx skilllint@latest check plugins/python-engineering/skills/*/SKILL.md
```

### Task 5: Decide on Gaps

These need a decision — create the content or remove the references:

| Missing file | Referenced from | Decision needed |
|-------------|----------------|-----------------|
| `pandas-patterns.md` | python3-data/SKILL.md | Create or remove ref |
| `web-patterns.md` | python3-web/SKILL.md | Create or remove ref |
| `async-testing.md` | python3-testing/SKILL.md | Create or remove ref |
| `mutation-testing.md` | python3-testing/SKILL.md | Create or remove ref |
| Remaining hatchling refs (~75 files) | Not referenced | Old plugin had 100+ files across 25 subdirs; only 3 subdirs migrated. Decide if rest needed. |

---

## Key Files

| Purpose | Path |
|---------|------|
| Architecture plan | `plugins/python3-development/python_plugin_redesign.md` |
| New plugin root | `plugins/python-engineering/` |
| Old plugin (intact) | `plugins/python3-development/` |
| Plugin manifest | `plugins/python-engineering/.claude-plugin/plugin.json` |
| Core router | `plugins/python-engineering/skills/python3-core/SKILL.md` |
| Plugin-level reference | `plugins/python-engineering/references/design-standards.md` |
| Template with stale pins | `plugins/python-engineering/assets/templates/pyproject.toml.j2` |
| Template with stale revs | `plugins/python-engineering/assets/templates/pre-commit-config.yaml` |

## Key Decisions Already Made

1. **One router, not three** — `python3-core` replaces `python3-development` + `specialist-skill-routing` + embedded agent routing
2. **`user-invocable: false`** for specialists — stays in context for auto-invocation, hidden from `/` menu
3. **`disable-model-invocation: true`** for manual entrypoints — completely invisible to auto-invocation
4. **Skills under 500 lines** — per official best practices; detail pushed to `references/`
5. **References one level deep** — no nested reference hierarchies
6. **Version 9.1.0** — continuation of old plugin's version sequence
7. **Backward-compat skills kept** — `modernpython`, `shebangpython`, `stinkysnake`, `snakepolish` preserved as-is

## Gotchas

- The `plugin.json` has no `"skills"` array — it was removed in a previous edit. This may need to be re-added depending on the plugin spec requirements. The old plugin's plugin.json also didn't have one (skills are auto-discovered from `skills/*/SKILL.md`).
- `python3-core/references/python3-standards.md` shows as modified (unstaged change) while all other files are staged additions.
- The `python3-data` and `python3-web` skills have **zero reference files** — their `references/` dirs are empty. These are the thinnest skills and may need content or should be merged into `python3-core`.
- Agent files use `skills:` arrays with `python-engineering:<skill-name>` namespace format.
