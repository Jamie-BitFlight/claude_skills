---
name: python3-stdlib-only
description: Use when building dependency-free Python 3.11+ scripts for airgapped, stdlib-only, or restricted environments where third-party package installation is prohibited — triggers on "stdlib-only", "airgapped", "no dependencies", "no internet", "restricted environment", or confirmed environments where external packages cannot be installed.
user-invocable: false
---

# Constrained / Legacy Environments

Consult `python3-core` for standing defaults.

**This skill is a LAST RESORT.** Use ONLY when confirmed environment restrictions prevent dependency installation. Do not assume restrictions — verify with the user first.

```mermaid
flowchart TD
    Start([Need Python CLI script]) --> Q1{Environment allows network access<br>for dependency installation?}
    Q1 -->|Yes — standard environment| UseTyper[Use python3-cli with Typer+Rich<br>Less code, better UX, well-tested libraries]
    Q1 -->|No| Q2{Restriction type confirmed?}
    Q2 -->|No — assumption only| Stop[STOP — Verify with user first<br>Do not assume restrictions]
    Q2 -->|Yes — airgapped/no internet/no uv| StdLib[Use stdlib-only patterns]
```

## Role

Create portable, dependency-free Python 3.11+ scripts that use only standard library at runtime. All code passes `ruff check` and the project type checker (**ty** or **mypy** / **pyright** per repo), with comprehensive pytest coverage.

**Fundamental principle:** Patterns are tools, not goals. Prefer simplicity, clarity, maintainability, and pragmatism over pattern correctness.

## Dependency Policy

- **Runtime:** Standard library ONLY (no external packages)
- **Dev-only:** pytest, ruff, ty (preferred), mypy or pyright when matching the host project
- **Runtime exceptions:** Only if essential, with explicit written justification and pinning strategy

## Required Behavior

- Preserve compatibility before applying modernization patterns
- Prefer stdlib solutions when dependency policy is restrictive
- Choose typing features valid for the project floor
- Make boundary wrappers explicit when Pydantic is unavailable
- Avoid recommending tools or syntax that exceed the project lane

---

## Working Process

### PHASE 0: Research

- Grep existing codebase for patterns to reuse
- List edge cases, integration points, and permission issues

### PHASE 1: Refactor Sanity Check

- Measure lines, branches, redundancy, and readability
- Apply only changes that reduce duplication or improve clarity
- Walrus, DRY, SRP rules enforced with justification

Required report:

```text
REFACTORING IMPACT ANALYSIS:
- Line count: X -> Y (∆ Z)
- Functions affected: N
- Patterns applied: [...]
- Complexity reduction: [...]
- Rejected changes: [reasons]
```

### PHASE 2: Creation

- Confirm Python 3.11+ requirement
- Ensure no forbidden typing imports
- Design: argparse CLI, structured logging, error boundaries, config handling
- Async only for I/O-bound operations

### PHASE 3: Validation

Automated:

```bash
python -m py_compile <file>
grep -E "from typing import .*(Dict|List|Set|Tuple|Optional|Union)\b" <file>
ruff check <file>
# Type check: match the host project — ty is default (`uv run ty check <file>`);
# use `mypy --strict <file>` when the project standardizes on mypy or uv is unavailable.
```

Checklist:

- Docstrings present
- CLI help works
- Unit tests for normal, edge, and error paths
- Cross-platform path handling
- Validation output shown

Required validation output:

```text
VALIDATION REPORT:
✅ Syntax check: PASSED
✅ Forbidden patterns: NONE FOUND
✅ Native type hints: VERIFIED (X instances)
✅ Ruff: PASSED
✅ Type check (ty or mypy): PASSED
✅ Checklist items: COMPLETED
```

---

## System Integration Patterns

### Stdlib CLI

```python
import argparse


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tool description", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    return parser
```

### Stdlib Logging

```python
import logging
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=handlers,
    )
```

### Stdlib Config

```python
import json, configparser, tomllib
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    ext = path.suffix.lower()
    data = path.read_text()
    if ext == ".json":
        return json.loads(data)
    if ext == ".toml":
        return tomllib.loads(data)
    if ext in (".ini", ".cfg"):
        p = configparser.ConfigParser()
        p.read_string(data)
        return {sec: dict(p[sec]) for sec in p.sections()}
    raise ValueError(f"Unsupported config format: {ext}")
```

### Privileged Command Execution

```python
from shutil import which
import os, subprocess


def run_privileged_command(cmd: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    if os.name != "posix":
        return subprocess.run([cmd, *args], capture_output=True, text=True)
    if os.geteuid() == 0:
        full = [cmd, *args]
    elif sudo := which("sudo"):
        full = [sudo, "-n", cmd, *args]
    else:
        full = [cmd, *args]
    return subprocess.run(full, capture_output=True, text=True, check=False)
```

### Errors

```python
import logging, sys


class ScriptError(Exception):
    """Base error for script-related failures."""


def handle_error(err: Exception, logger: logging.Logger) -> None:
    logger.error(f"Error: {err}")
    if logger.isEnabledFor(logging.DEBUG):
        logger.exception("Traceback")
    sys.exit(1)
```

### Async

```python
import asyncio
from collections.abc import Coroutine
from typing import Any


async def run_async(tasks: list[Coroutine[Any, Any, Any]]) -> list[Any]:
    return await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Multi-File Project Skeleton

When PEP 723 single-file approach is insufficient:

```text
project_name/
├── main.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_setup.py
│   └── exceptions.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── test_core.py
├── config.example.toml
└── README.md
```

---

## Code Quality Standards

- Pass `ruff check` and type checking clean (`ty` or `mypy --strict` per project)
- Google-style docstrings for modules, classes, and functions
- Use structural pattern matching, dataclasses, and walrus operator only if they reduce complexity and increase clarity
- Follow PEP 8

---

## Testing Standards

Pytest with coverage of normal, edge, and error cases.

```python
import json
from pathlib import Path
from module import load_config


def test_load_json(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"k": "v"}))
    result = load_config(path)
    assert result == {"k": "v"}
```

---

## Shebang

Stdlib-only scripts use `#!/usr/bin/env python3` (no PEP 723 metadata — nothing to declare).

Validate with `/python-engineering:shebangpython <file_path>`.

---

## Boundaries

- No deprecated syntax
- No platform-specific behavior without fallbacks
- No skipping validation or tests
- No delivery without a full Validation Report

---

## References

- `references/command-execution.md` — timeout handling, privilege elevation, logging, type-safe command building
- `references/type-safety-patterns.md` — overloads, protocols, type narrowing, linter settings
- `references/typing-strategy.md` — Protocol vs TypeVar vs ParamSpec, abstract collections, Any boundaries, JSON handling
