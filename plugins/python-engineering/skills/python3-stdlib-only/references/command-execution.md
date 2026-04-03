---
title: Command Execution Patterns
description: Timeout, elevation, logging, and type-safe command building for stdlib scripts
version: 1.0.0
last_updated: '2026-02-15'
document_type: reference
python_compatibility: 3.11+
---

# Command Execution Patterns

Goals: clear types, predictable logging, minimal privilege, portable behavior.

## Basic Command Execution

```python
import os
import subprocess
from shutil import which
from collections.abc import Sequence
from typing import TypeAlias

StrPath: TypeAlias = str | os.PathLike[str]
Cmd: TypeAlias = Sequence[StrPath]

def run_cmd(cmd: Cmd, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run a command with timeout and text capture."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
```

## Privileged Execution

```python
def run_cmd_elevated(cmd: Cmd, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run a command with privilege elevation on POSIX when available, else run as-is."""
    if os.name != "posix":
        return run_cmd(cmd, timeout)
    if os.geteuid() == 0:
        return run_cmd(cmd, timeout)
    if (sudo := which("sudo")):
        return run_cmd([sudo, "-n", *map(str, cmd)], timeout)
    return run_cmd(cmd, timeout)
```

## Logging Adapter Pattern

Inject a logger-like object with `.info`/`.debug` methods to decouple from logging backends.

Keep log messages side-effect free. Log the joined command using `map(str, cmd)`.

```python
from typing import Protocol

class LoggerLike(Protocol):
    def debug(self, msg: str) -> None: ...
    def info(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...

def run_with_log(logger: LoggerLike, cmd: Cmd, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    logger.info(f"running: {' '.join(map(str, cmd))} (timeout {timeout}s)")
    return run_cmd(cmd, timeout)
```

## Security and Ergonomics

- Never assume sudo exists or succeeds
- Do not prompt for passwords in non-interactive scripts
- Use `check=False` by default; inspect returncode explicitly and produce actionable errors
- Bound timeouts; never run unbounded commands in CI paths

## Complete Example

```python
import os
import subprocess
from shutil import which
from collections.abc import Sequence
from typing import TypeAlias, Protocol

StrPath: TypeAlias = str | os.PathLike[str]
Cmd: TypeAlias = Sequence[StrPath]

class LoggerLike(Protocol):
    def info(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...

def run_cmd(cmd: Cmd, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)

def run_cmd_elevated(cmd: Cmd, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run with privilege elevation if needed."""
    if os.name != "posix":
        return run_cmd(cmd, timeout)
    if os.geteuid() == 0:
        return run_cmd(cmd, timeout)
    if (sudo := which("sudo")):
        return run_cmd([sudo, "-n", *map(str, cmd)], timeout)
    return run_cmd(cmd, timeout)

def run_with_log(logger: LoggerLike, cmd: Cmd, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run command with logging."""
    logger.info(f"running: {' '.join(map(str, cmd))} (timeout {timeout}s)")
    result = run_cmd(cmd, timeout)
    if result.returncode != 0:
        logger.error(f"command failed: {result.stderr}")
    return result
```
