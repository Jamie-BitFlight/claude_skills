---
name: shebangpython
description: Validates Python shebangs and PEP 723 inline script metadata. Use when creating or validating standalone executable Python scripts. Ensures shebang matches script type.
argument-hint: '<file-path>'
user-invocable: true
---

# Shebang & PEP 723 Validation

Validate the shebang for ALL Python scripts based on their dependencies.

## Input

File: $ARGUMENTS

## Rules

| Script Type | Shebang | PEP 723 |
|---|---|---|
| Stdlib-only | `#!/usr/bin/env python3` | None (nothing to declare) |
| With dependencies | `#!/usr/bin/env -S uv --quiet run --active --script` | Required (lists deps) |
| Package executables | `#!/usr/bin/env python3` | None (deps via package manager) |
| Library modules | No shebang | None |

## Actions

1. Analyze imports to determine dependency type
2. Correct shebang if wrong
3. Add PEP 723 metadata if external deps detected
4. Remove PEP 723 metadata if stdlib-only
5. Set execute bit if needed
