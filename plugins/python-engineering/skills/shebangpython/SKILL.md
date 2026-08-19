---
name: shebangpython
description: Validates and corrects Python shebangs and PEP 723 inline script metadata by applying four shebang-selection rules. Use when auditing or fixing shebangs in Python files — choosing between plain python3 and the uv shebang for standalone scripts with external dependencies, adding or removing PEP 723 metadata blocks to match actual import requirements, checking execute bit presence, or avoiding redundant transitive dependencies when typer is declared (typer bundles rich and shellingham automatically).
argument-hint: '[file-paths...]'
user-invocable: true
---

<file_paths>$ARGUMENTS</file_paths>

# Python Shebang Validation

The model validates Python shebangs against dependency requirements and ensures correct PEP 723 inline script metadata.

## Arguments

<file_paths/>

## Instructions

If file paths provided above:

1. Read each file using the Read tool
2. Check for shebang presence and correctness
3. Validate against the rules below
4. Check execute bit status
5. Fix any misalignments with this guidance
6. Report findings for each file

If no arguments provided:

1. Ask the user which files or directories need shebang validation
2. Suggest searching for Python files that might need shebangs
3. Offer to check if existing shebangs are correct

---

## Shebang Selection Rules

### Rule 1: Stdlib-only executable scripts

**Pattern**: `#!/usr/bin/env python3`

**Conditions**:

- File is executable
- Has no external dependencies
- Uses only Python standard library

**Reasoning**: No dependency installation required, standard Python interpreter sufficient.

### Rule 2: Package executables

**Pattern**: `#!/usr/bin/env python3`

**Conditions**:

- File is part of installed package
- Has setup.py or pyproject.toml managing dependencies

**Reasoning**: Dependencies installed via package manager, not script metadata.

### Rule 3: Standalone scripts with external dependencies

**Pattern**: `#!/usr/bin/env -S uv run --quiet --script`

**Conditions**:

- File is executable standalone script
- Requires external packages

**Reasoning**: PEP 723 inline metadata declares dependencies, uv installs them automatically.
Never add `--active`: it makes `uv run` prefer an ambient activated virtual environment over the
isolated ephemeral one PEP 723 scripts are supposed to get, installing the script's dependencies
into the caller's shared `.venv` instead of a throwaway environment — empirically verified: a
probe script declaring a dependency absent from a project venv, run under `--active --script`
with `VIRTUAL_ENV` set, measurably installed into that venv; with `--active` omitted, the same
probe resolved into an isolated `uv` cache environment instead, leaving the project venv
untouched.

### Rule 4: Non-executable files

**Pattern**: No shebang line

**Conditions**:

- File is library module
- Imported by other code
- Not directly executable

**Reasoning**: Not intended for direct execution.

---

## UV Shebang Command Structure

The shebang: `#!/usr/bin/env -S uv run --quiet --script`

### Component Breakdown

| Component           | Position    | Purpose                                                        |
| -------------------- | ----------- | ---------------------------------------------------------------|
| `#!/usr/bin/env -S`  | Prefix      | Shebang invoking env with -S flag for multiple arguments       |
| `uv`                 | Command     | The uv binary on PATH                                          |
| `run`                | Subcommand  | Executes Python scripts with automatic environment management  |
| `--quiet`            | Global flag | Suppresses progress output from uv                             |
| `--script`           | run flag    | Indicates file contains PEP 723 inline script metadata         |

### Flag Ordering

`--quiet`/`-q` is a global option — `uv --help` and `uv run --help` list it identically, and
`uv run --quiet --script` / `uv --quiet run --script` are confirmed equivalent at runtime (both
exit 0, identical output). Either ordering works; use `uv run --quiet --script` as the canonical
form for consistency.

### Invalid Variations

The model MUST reject any shebang carrying `--active` in any position — it breaks PEP 723
isolation (see Rule 3 above) — and any PEP-723-metadata file missing `--script`.

---

## Execute Bit Requirement

All files with shebangs MUST have execute permission set.

```bash
chmod +x filename
```

Without execute bit, the shebang is ignored by the kernel.

---

## Mandatory Verification Format

For each file, output in this exact order:

1. **Current shebang**: [exact line from file or "none"]
2. **PEP 723 metadata dependencies**: [exact list or "none"]
3. **External package count**: [number with evidence]
4. **Import analysis**:
   - stdlib: [list]
   - external: [list]
5. **Rule condition evaluation**:
   - Rule 1: [condition 1 MET/NOT MET] [condition 2 MET/NOT MET] [condition 3 MET/NOT MET]
   - Rule 2: [condition 1 MET/NOT MET] [condition 2 MET/NOT MET]
   - Rule 3: [condition 1 MET/NOT MET] [condition 2 MET/NOT MET]
   - Rule 4: [condition 1 MET/NOT MET]
6. **Applicable rule**: [number] because [one-sentence justification citing specific unmet/met conditions]
7. **Execute bit**: [executable/not executable via test command]
8. **Verdict**: CORRECT / INCORRECT [if incorrect, Edit the file to fix]

---

## Transformation Examples

### Example 1: Remove redundant PEP 723 from stdlib-only script

**Before** (invalid - no external dependencies):

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

from __future__ import annotations

import re
from pathlib import Path
```

**After** (corrected):

```python
#!/usr/bin/env python3

from __future__ import annotations

import re
from pathlib import Path
```

---

## Bundled Transitive Dependency Constraint

`typer>=0.12.0` ships with `rich` and `shellingham` as bundled transitive dependencies. When `typer` appears in a PEP 723 `dependencies` block, the model MUST NOT add `rich` or `shellingham` as separate entries.

```python
# WRONG — rich is transitively installed by typer
# dependencies = [
#   "typer>=0.21.2",
#   "rich>=13.0.0",   # redundant, DO NOT ADD
# ]

# CORRECT — typer only; rich and shellingham arrive automatically
# dependencies = [
#   "typer>=0.21.2",
# ]
```

This rule applies regardless of how much rich API surface the script uses (`Console`, `Panel`, `Progress`, `Table`, etc.). The import works because typer guarantees rich's presence.

SOURCE: "By default, `typer` comes with `rich` and `shellingham`." — <https://typer.tiangolo.com/#installation> (accessed 2026-02-22)

---

### Example 2: Add PEP 723 to script with external dependencies

**Before** (invalid - missing PEP 723):

```python
#!/usr/bin/env python

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
```

**After** (corrected):

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.2",
# ]
# ///

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
```

---

## References

- [PEP 723 - Inline Script Metadata](https://peps.python.org/pep-0723/)
- [uv CLI Reference](https://docs.astral.sh/uv/reference/cli/)
- [uv run Subcommand](https://docs.astral.sh/uv/reference/cli/#uv-run)
