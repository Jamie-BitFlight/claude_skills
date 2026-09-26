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

Repository configuration is authoritative. Runtime discovery is read-only and distinguishes complete discovery, no applicable gates, and incomplete/unsupported discovery. The bundled `discover_linters.py` utility writes setup documentation and is not the runtime discovery API. A passing command may still emit advisory diagnostics; gate status and diagnostic disposition are reported separately.

Typical configured tools can include Ruff, MyPy, Pyright/BasedPyright, Bandit, ESLint, Prettier, ShellCheck, shfmt, Markdownlint, pre-commit, or prek. This list is illustrative, not a hardcoded contract.

## Failure routing

Related diagnostics may share a cause across files; files are therefore not the default concurrency boundary. Cluster by causal surface before parallel correction.

For Python, route implementation judgment to Python Engineering. Broader independent review such as StinkySnake or SnakePolish is appropriate only when the demonstrated scope warrants it, not for every lint failure.

## Verification

Completion reports scope, discovery status, gates/results, diagnostic dispositions, correction-integrity evidence, unresolved items, out-of-scope delivery/return status, and additional validation. Missing required evidence, authority, or capability produces a blocked status rather than a manufactured pass.

A passing rerun verifies only the exercised gate and scope; it is not general proof of architecture correctness.
## Legacy machinery

The core skill no longer depends on the former CLAUDE.md-driven `lint_orchestrator.py` executor or the standalone `install_agents.py` copier. Those scripts were retired rather than repaired because the rebuilt runtime uses host plugin discovery and repository configuration directly. `discover_linters.py` remains a separately authorized setup/documentation utility, not runtime discovery.


### Retired standalone CLI compatibility

The removed `lint_orchestrator.py` and `install_agents.py` interfaces are intentionally unsupported after this migration. No active in-repository caller was found during the retirement review, but repository search cannot prove absence of external installations. External users should migrate lint execution to `/holistic-linting:holistic-linting` and agent availability to normal host plugin installation/discovery. The old CLAUDE.md LINTERS executor and manual agent-copy/hash/`--force` contracts are not compatibility guarantees of the rebuilt plugin.

This is an explicit retirement decision, not a claim of behavioral equivalence. Historical planning/research references may continue to describe those scripts at older revisions.
