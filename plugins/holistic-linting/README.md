# Holistic Linting

Holistic Linting discovers and runs the quality gates a repository actually configures, preserves failures as evidence, routes diagnosis to the capability that owns the affected domain, and reruns affected gates to verify corrections.

## What it owns

```text
changed/requested work
  -> discover configured gates
  -> execute
  -> preserve diagnostics
  -> cluster related failures
  -> route diagnosis/correction
  -> rerun affected gates
  -> report observed result
```

The plugin does not define Python engineering standards or maintain its own general root-cause methodology. Python-specific design belongs to the Python Engineering plugin. Non-trivial causal investigation routes through Development Harness when that capability is available.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system boundaries and invariants.

## Quality-gate integrity

A diagnostic is evidence from a tool, not proof of product intent or of the correct local edit. Corrections must preserve the governing product/repository contract.

The workflow does not autonomously suppress, downgrade, bypass, or narrow configured quality gates to manufacture a green result. When valid behavior requires a quality-policy exception, it reports the evidence and authorization needed rather than distorting production code.

Unresolved and out-of-scope diagnostics remain visible.

## Installation

For Claude Code:

    /plugin marketplace add Jamie-BitFlight/claude_skills
    /plugin install holistic-linting@jamie-bitflight-skills

The core plugin requires a supported plugin host plus the quality tools configured by the target repository. Python Engineering and Development Harness improve domain/causal routing when installed; they are optional external capabilities. When absent, continue within bounded local evidence or report the missing capability when it is necessary for a safe decision.

Repository co-location alone does not prove cross-plugin invocation in a separately installed host.

## Usage

Invoke the core skill directly:

```text
/holistic-linting:holistic-linting <scope>
```

The existing `/lint` command and compatibility orchestrator/resolver entry points remain available while callers migrate to the core skill.

## Discovery and execution

Repository configuration is authoritative. Runtime discovery is read-only and distinguishes complete discovery, no applicable gates, and incomplete/unsupported discovery. A passing command may still emit advisory diagnostics; gate status and diagnostic disposition are reported separately.

Typical configured tools can include Ruff, MyPy, Pyright/BasedPyright, Bandit, ESLint, Prettier, ShellCheck, shfmt, Markdownlint, pre-commit, or prek. This list is illustrative, not a hardcoded contract.

## Failure routing

Related diagnostics may share a cause across files; files are therefore not the default concurrency boundary. Cluster by causal surface before parallel correction.

For Python, route implementation judgment to Python Engineering. Broader independent review such as StinkySnake or SnakePolish is appropriate only when the demonstrated scope warrants it, not for every lint failure.

## Verification

Completion reports scope, discovery status, gates/results, diagnostic dispositions, correction-integrity evidence, unresolved items, out-of-scope delivery/return status, and additional validation. Missing required evidence, authority, or capability produces a blocked status rather than a manufactured pass.

A passing rerun verifies only the exercised gate and scope; it is not general proof of architecture correctness.

## Retired scripts

Three standalone scripts were retired. Their interfaces are unsupported and are not compatibility guarantees of the rebuilt plugin:

- `lint_orchestrator.py` executed tools listed in a CLAUDE.md `## LINTERS` section.
- `discover_linters.py` generated that `## LINTERS` section. Its only reader was `lint_orchestrator.py`.
- `install_agents.py` copied the resolver agent into `.claude/agents/` with hash comparison and `--force` overwrite.

Migrate as follows:

- Lint execution: invoke `/holistic-linting:holistic-linting`. It inspects repository configuration directly; no CLAUDE.md section is needed.
- Agents on Claude Code: install the plugin. Claude Code auto-discovers the plugin's `agents/` directory, so no copy step is needed.
- Codex: the Codex manifest (`.codex-plugin/plugin.json`) declares skills only, and the Codex plugin manifest format has no agents field. Load the `holistic-linting` skill directly; callers of the former resolver agent use the `holistic-linting-resolver` skill.

Retirement decisions and their evidence are recorded in [evals/portability-and-corpus.md](./evals/portability-and-corpus.md#retired-script-decisions). This is a retirement, not a claim of behavioral equivalence. Historical planning/research references may continue to describe those scripts at older revisions.
