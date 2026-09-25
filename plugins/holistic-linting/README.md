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

## Usage

Invoke the core skill directly:

```text
/holistic-linting:holistic-linting <scope>
```

The existing `/lint` command and compatibility orchestrator/resolver entry points remain available while callers migrate to the core skill.

## Discovery and execution

The plugin can use its bundled deterministic helpers to discover configured checks and select a pre-commit-compatible runner. Repository configuration remains authoritative. Run checks at the smallest useful scope unless the repository's configured gate or the user requires a broader run.

Typical configured tools can include Ruff, MyPy, Pyright/BasedPyright, Bandit, ESLint, Prettier, ShellCheck, shfmt, Markdownlint, pre-commit, or prek. This list is illustrative, not a hardcoded contract.

## Failure routing

Related diagnostics may share a cause across files; files are therefore not the default concurrency boundary. Cluster by causal surface before parallel correction.

For Python, route implementation judgment to Python Engineering. Broader independent review such as StinkySnake or SnakePolish is appropriate only when the demonstrated scope warrants it, not for every lint failure.

## Verification

Completion reports the scope, configured gates executed, observed result, resolved diagnostics, unresolved diagnostics, out-of-scope diagnostics, and any additional validation still required.

A passing rerun verifies only the exercised gate and scope; it is not general proof of architecture correctness.
