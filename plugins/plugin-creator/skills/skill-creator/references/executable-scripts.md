# Executable Scripts in Skills

Guidance for skills that bundle executable scripts alongside instruction files.
If your skill uses only markdown instructions, this file does not apply.

## Table of Contents

- [Solve, Don't Punt](#solve-dont-punt)
- [Utility Scripts](#utility-scripts)
- [Visual Analysis](#visual-analysis)
- [Verifiable Intermediate Outputs](#verifiable-intermediate-outputs)
- [Package Dependencies](#package-dependencies)
- [Avoid Assuming Tools Are Installed](#avoid-assuming-tools-are-installed)

---

## Solve, Don't Punt

When a script encounters an error, handle it rather than letting the failure propagate to Claude as an unhandled exception.

Claude receiving a raw traceback must interpret the error, decide what to do, and attempt a recovery — all from conversational context. A script that handles its own errors is faster, more reliable, and produces clearer outcomes.

**Handle errors explicitly:**

```python
def load_config(path):
    """Load config file, creating a default if missing."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Config not found at {path}, creating default")
        with open(path, "w") as f:
            f.write("{}")
        return "{}"
    except PermissionError:
        print(f"Cannot read {path} — check file permissions")
        return "{}"
```

**Do not punt to Claude:**

```python
def load_config(path):
    # Unhandled exceptions become Claude's problem
    return open(path).read()
```

Configuration constants must be self-documenting. Magic numbers with no explanation cannot be validated or adjusted.

**Self-documenting constants:**

```python
# HTTP requests typically complete within 30 seconds
# Longer timeout accounts for slow or congested connections
REQUEST_TIMEOUT = 30

# Three retries balances reliability against latency
# Most transient failures resolve by the second attempt
MAX_RETRIES = 3
```

**Unexplained constants:**

```python
TIMEOUT = 47  # Why 47?
RETRIES = 5  # Why 5?
```

If you cannot justify the value, Claude cannot either. Document the rationale or pick a well-known default.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

---

## Utility Scripts

Pre-built scripts outperform on-the-fly code generation in every operational dimension:

- **Reliability** — tested, version-controlled code behaves consistently
- **Token efficiency** — scripts execute without loading their source into context; only output consumes tokens
- **Speed** — no generation step; execution begins immediately
- **Consistency** — identical behavior across every invocation

**Directory layout:**

```text
my-skill/
├── SKILL.md
└── scripts/
    ├── extract_data.py     # Extract structured data from input
    ├── validate_plan.py    # Validate plan file before execution
    └── apply_changes.py    # Apply validated changes to target
```

**Execute vs. read distinction:**

Instructions must be explicit about which action Claude should take:

- **Execute** (most common): `Run scripts/extract_data.py to extract field definitions`
- **Read as reference** (for complex logic): `See scripts/extract_data.py for the extraction algorithm`

Execution is preferred because the script runs autonomously and only its output enters context. Reading loads the full source — use this only when Claude needs to understand the implementation.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

---

## Visual Analysis

When inputs have spatial structure — layouts, forms, diagrams, rendered tables — Claude's vision capabilities often outperform markup parsing.

Convert the input to an image and let Claude analyze it visually:

````markdown
## Layout analysis

1. Convert the source file to images:

   ```bash
   python scripts/render_to_images.py input_file
   ```

2. Analyze each page image to identify field locations and types
3. Claude can see layout, position, and grouping directly from the visual
````

Use this pattern when:

- The layout of elements matters (not just their values)
- Parsing the raw format is error-prone or brittle
- Spatial relationships (adjacency, alignment, nesting) carry semantic meaning

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

---

## Verifiable Intermediate Outputs

For complex, multi-step, or high-stakes operations, use the plan-validate-execute pattern. Claude creates a structured plan first, a script validates it before any changes are applied, and execution proceeds only after validation passes.

**Why this works:**

- Catches errors before they touch production data
- Validation is machine-objective, not conversational
- Claude iterates on the plan file, not on partially-applied changes
- Specific error messages let Claude fix problems precisely

**When to use:**

Batch operations, destructive changes, complex validation rules, high-stakes operations where partial failure is costly.

**Pattern:**

```text
analyze → create plan file → validate plan → execute → verify
```

**Example workflow documentation:**

````markdown
## Update workflow

1. Run `scripts/extract_schema.py input_file > schema.json`
2. Create `changes.json` listing all updates to apply (see schema below)
3. Run `scripts/validate_changes.py schema.json changes.json`
   - If validation fails, revise `changes.json` and repeat step 3
   - If validation passes, continue
4. Run `scripts/apply_changes.py schema.json changes.json output_file`
5. Run `scripts/verify_output.py output_file` to confirm result
````

**Validation script output quality matters:**

Write verbose, specific error messages:

```text
Field 'due_date' not found. Available fields: created_at, updated_at, completed_at
Value '2026-13-01' is not a valid date. Expected format: YYYY-MM-DD
```

Vague errors require Claude to guess. Specific errors let Claude fix and retry autonomously.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

---

## Package Dependencies

Skills execute in the code execution environment. Package availability depends on platform:

- **claude.ai** — can install packages from npm and PyPI and pull from GitHub repositories at runtime
- **Claude API** — no network access and no runtime package installation; packages must be pre-installed

Declare required packages explicitly in SKILL.md. Verify availability against the [code execution tool documentation](https://docs.anthropic.com/en/agents-and-tools/tool-use/code-execution-tool).

**In SKILL.md:**

```markdown
## Requirements

Required packages (install before use):

- `pip install ruamel.yaml` — YAML read/write with comment preservation
- `pip install httpx` — HTTP client for API calls
```

Listing dependencies in SKILL.md serves two purposes: users know what to install, and Claude knows what is available when deciding how to proceed.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

---

## Avoid Assuming Tools Are Installed

Never assume a package or CLI tool is present in the execution environment. Always provide the install command alongside usage instructions.

**State the dependency and how to satisfy it:**

````markdown
Install the required package:

```bash
pip install ruamel.yaml
```

Then use it:

```python
from ruamel.yaml import YAML

yaml = YAML()
with open("config.yaml") as f:
    config = yaml.load(f)
```
````

**Do not assume installation:**

```markdown
Use ruamel.yaml to parse the config file.
```

For CLI tools, provide the install command and a fallback when one exists:

````markdown
This step requires `jq` for JSON processing.

Install:

```bash
# macOS
brew install jq

# Debian/Ubuntu
apt-get install jq
```

If `jq` is not available, use the Python fallback:

```bash
python scripts/process_json.py input.json
```
````

Providing a fallback is especially important for skills targeting Claude API environments where package installation may not be possible.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)
