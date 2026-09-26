# Portability and retained-reference evaluation

This document defines the evidence required before retiring compatibility entry points or the bundled Ruff/MyPy/Bandit reference corpus. It does not claim those evaluations have run.

## Supported-host matrix

For each supported host, test these installation sets against the same pinned plugin revision:

1. Holistic Linting only.
2. Holistic Linting + Python Engineering.
3. Holistic Linting + Development Harness.
4. All three plugins.

For each set record:

- host and version;
- plugin installation evidence;
- whether the core skill is discoverable;
- whether optional cross-plugin skills are discoverable through the host's supported mechanism;
- [E13](./behavioral-cases.md) task/result;
- file-only compatibility invocation and supplied-evidence invocation;
- DONE/BLOCKED result and evidence;
- whether any source-tree-relative assumption was required.

A monorepo checkout is not evidence that separately installed plugins can invoke one another.

## Compatibility retirement

The compatibility surfaces are:

- `holistic-linting-orchestrator`;
- `holistic-linting-resolver`;
- `linting-root-cause-resolver`;
- `post-linting-architecture-reviewer`.

Before retiring one:

1. Search current repository callers.
2. Exercise its declared legacy input contract.
3. Compare the resulting observable outcome with direct core invocation.
4. Record known external/public compatibility risk separately; repository search cannot prove absence of external callers.
5. Migrate known callers before deletion.

Retain an adapter only when it preserves a demonstrated caller contract or host boundary that the core entry point cannot replace directly.

## Rule corpus evaluation

Do not evaluate the corpus by file count alone. Sample configured-tool/version cases that discriminate among:

- installed/current authoritative documentation;
- offline bundled fallback;
- stale or version-mismatched bundled guidance;
- missing evidence.

At minimum run:

- Ruff rule lookup with installed `ruff rule`;
- MyPy online/current-version lookup and offline fallback;
- Bandit current evidence and offline fallback;
- unknown/new rule code absent from the corpus.

For each case record whether the bundled material changes task correctness, prevents guessing, or merely duplicates current authoritative output. Retire only material whose protected offline/version-sensitive behavior has an equivalent carrier.

## Decision outputs

Each compatibility surface and corpus family receives one of:

- **RETAIN** - demonstrated unique value;
- **REDUCE** - only a bounded subset provides unique value;
- **RELOCATE** - behavior belongs to another owning plugin/capability;
- **RETIRE** - equivalent behavior is demonstrated without it;
- **UNRESOLVED** - evidence is insufficient.

Do not infer runtime-token or latency savings from source deletion; measure those separately if they matter.

## Retired-script decisions

These records apply the compatibility retirement procedure above to the three standalone scripts this change deletes. They were written after the deletion. The legacy scripts were run from their last revision (`29c775fe5`) against a scratch Git repository containing `pyproject.toml` (with `[tool.ruff]`) and `a.py`, on macOS with `uv`. Direct core invocation (step 3) is a live-host skill run, and no such run was performed. No record claims behavioral equivalence.

### `discover_linters.py` - RETIRE

1. Callers: repository search found no invocation outside the plugin's own README/SKILL.md prose (removed here) and historical `.claude/plan/` research notes. Its output, the CLAUDE.md `## LINTERS` section, was parsed only by `lint_orchestrator.py` (`parse_linters_section`).
2. Legacy contract, exercised: `discover_linters.py --output CLAUDE.md` in a fresh repository exited 1 with `NoOptionError: No option 'hooksPath' in section: 'core'`. After setting `core.hooksPath`, it exited 0 and wrote a `## LINTERS` section listing `ruff format [*.py]` and `ruff check [*.py]`.
3. Core comparison: not run. The core skill does not read a `## LINTERS` section; it inspects repository configuration directly, so this output has no consumer once `lint_orchestrator.py` is removed.
4. External risk: repository search cannot rule out external users who run the script to document linters. That use is unsupported after retirement.
5. Known callers migrated: none found.

### `lint_orchestrator.py` - RETIRE

1. Callers: no invocation found outside historical `.claude/plan/` research notes.
2. Legacy contract, exercised: without a CLAUDE.md it exited 1 with `CLAUDE.md not found`. With the section generated above, `lint_orchestrator.py a.py` attempted `ruff format` and `ruff check` through the project environment, and exited 1 when `ruff` could not be spawned there (`Found 2 errors`).
3. Core comparison: not run. The core executes repository-configured gates and reports discovery status and diagnostic dispositions, which this script's contract does not provide. That is a difference in contract, not a measured equivalence.
4. External risk: repository search cannot rule out external callers. The CLAUDE.md-driven execution contract is unsupported after retirement.
5. Known callers migrated: none found.

### `install_agents.py` - RETIRE

1. Callers: no invocation found outside historical `.claude/plan/` research notes.
2. Legacy contract, exercised: `install_agents.py --scope project` exited 1 with `Agent source file not found`. The script resolves its source as `<skill>/agents/linting-root-cause-resolver.md`; at `29c775fe5` no skill-local `agents/` directory exists, because the agent lives in the plugin-root `agents/` directory. The copy contract was therefore already non-functional before deletion.
3. Core comparison: not applicable to a copier. The replacement is host plugin loading: Claude Code auto-discovers plugin `agents/`; the Codex manifest declares skills only, so Codex users load the `holistic-linting-resolver` skill. No fresh host-installation trial was run.
4. External risk: repository search cannot rule out external users of the copy/hash/`--force` behavior. It is unsupported after retirement.
5. Known callers migrated: none found.
