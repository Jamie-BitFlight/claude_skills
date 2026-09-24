<p align="center">
  <img src="./assets/hero.png" alt="Python Engineering" width="800" />
</p>

# Python Engineering

Opinionated Python engineering for coding agents: strong defaults, independent design challenge, typed boundaries, evidence-first testing, and deep quality/modernization audits.

Existing coherent projects keep their architecture and tooling. New work gets the plugin's preferred choices first.

## Start here

Install from the marketplace:

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install python-engineering@jamie-bitflight-skills
```

Then use one of two primary entry points:

```text
/python-engineering:orchestrate "Add a CLI command that processes CSV files"
/python-engineering:python-quality-audit PR
```

**`orchestrate` builds and changes Python.** It traces the affected system, challenges the plan independently, selects specialists, implements, tests, reviews, and validates.

**`python-quality-audit` investigates existing Python.** It is read-only and asks what is wrong, what can disappear, what modern Python can replace, and what mature ecosystem tooling can take off your maintenance burden.

## What you get

- **Opinionated defaults without forced rewrites.** Repository contracts and coherent existing architecture win; greenfield work starts from the plugin's preferred Python stack and design.
- **Adversarial design before implementation.** A separate agent traces callers, consumers, tests, docs, configuration, generated artifacts, manifests, and public contracts before accepting a plan as complete.
- **Agent-aware CLI design.** Tools inside Agent Skills/plugins emit compact JSON on stdout, preferably from Pydantic models; human-facing CLIs prefer Typer + Rich.
- **Typed boundaries.** Dynamic data is validated at explicit boundaries. Necessary typing/lint exceptions are localized by file rather than scattered through the codebase.
- **Evidence-first tests.** RED must fail for the expected behavioral reason. Coverage protects behavior and risk rather than chasing an invented percentage.
- **Pythonic design pressure.** SOLID, small cohesive modules, direct construction before abstraction, and ~500 physical LOC per source file as the default boundary.
- **Modernization that can delete code.** Audits look for obsolete compatibility layers, hand-built machinery replaceable by modern Python or maintained libraries, redundant process, and practices proven in substantial Python projects.

## Quality audit

This is the broad review entry point:

```text
/python-engineering:python-quality-audit PR
/python-engineering:python-quality-audit diff
/python-engineering:python-quality-audit staged
/python-engineering:python-quality-audit unstaged
/python-engineering:python-quality-audit src/
/python-engineering:python-quality-audit src/ "assess Python 3.15 as the proposed minimum"
```

It fans out independent investigators so one interpretation does not anchor the others:

```text
python-quality-audit
  ├─ StinkySnake       smells, standards drift, maintenance hazards
  ├─ SnakePolish       modern Python, stdlib and ecosystem opportunities
  ├─ ecosystem lane    maintained libraries that can replace local machinery
  ├─ project lane      how substantial Python projects solve the same problems
  └─ removal lane      dead code, compatibility and process that can disappear
       ↓
  evidence-backed synthesis
       ↓
  actionable findings + protected behavior + verification plan
```

Findings distinguish **OBSERVED**, **DERIVED**, **VERIFIED-EXTERNAL**, and **HYPOTHESIS** evidence. A material recommendation is not called actionable until its affected surface and verification path are known.

Use the individual lenses when you only need one:

```text
/python-engineering:stinkysnake src/myapp/processor.py
/python-engineering:snakepolish src/myapp/
```

Both are read-only. StinkySnake hunts smells and root causes; SnakePolish asks how the same behavior could require less code and maintenance.

## Engineering workflow

```text
orchestrate
   ↓
classify task + repository constraints
   ↓
architecture/design when material
   ↓
independent adversarial scope trace
   ↓
tests first when applicable
   ↓
implementation
   ↓
bounded code review
   ↓
repository checks + behavioral verification
```

The adversarial stage is intentionally difficult to skip. Its **investigation depth is fixed** while its **design ceremony is adaptive**: a two-line change still gets its callers and consequences traced, but it does not need an eleven-section architecture document unless the decisions justify one.

## Defaults

These are first choices for new work, not reasons to churn a coherent project.

| Area | Preferred default |
|---|---|
| Runtime | Project floor first; modern supported Python for greenfield work |
| Dependencies | `uv` |
| Lint / format | `ruff` |
| Type checking | `ty` |
| Tests | `pytest`; pytest-mock/Hypothesis when they strengthen the test |
| Build backend | Hatchling |
| Human CLI | Typer + Rich |
| Agent/plugin CLI | Compact JSON stdout; diagnostics on stderr |
| Structured boundary data | Pydantic when runtime validation/serialization earns it |
| TOML mutation | `tomlkit` |
| Module size | ~500 physical LOC; decompose by cohesive responsibility |
| Coverage | Changed behavior, boundaries and risk; respect project gates |
| Design | SOLID as design pressure, not an abstraction quota |

Precedence is explicit requirements/safety → repository contracts and established architecture → ecosystem conventions → plugin defaults.

## Design principles

### Keep the typed core clean

Prefer precise types. External/dynamic data enters through explicit validator/parser/adapter modules and becomes strongly typed immediately. If an integration genuinely requires `Any` or a lint exception, localize that exceptional code in a dedicated file and configure the narrowest file-level exception there.

### Don't cargo-cult privacy

A leading underscore is an architectural claim. Do not create `_helper`, `_client`, or `_thing` merely because implementation details are traditionally made "private." Require an actual API boundary, framework requirement, name-mangling need, or collision.

### Keep modules comprehensible as a whole

~500 physical LOC is the default source-file boundary, including docstrings. Approaching it triggers decomposition analysis. Larger files need evidence that splitting would damage cohesion or create a worse dependency/API boundary.

### Prefer deletion over another abstraction

Before adding a wrapper, factory, protocol, compatibility layer, parser, retry loop, serializer, or automation step, ask whether Python, the existing project, or a mature maintained library already owns the problem.

## Focused commands

| Command | Purpose |
|---|---|
| `/python-engineering:orchestrate` | Primary implementation/change workflow |
| `/python-engineering:python-quality-audit` | Broad read-only quality and modernization audit |
| `/python-engineering:review` | Bounded conventional code review |
| `/python-engineering:lint` | Deterministic check-only lint/type checks |
| `/python-engineering:debug` | Hypothesis-driven debugging |
| `/python-engineering:python3-tdd` | Explicit red-green-refactor workflow |
| `/python-engineering:stinkysnake` | Single-lens smell hunt |
| `/python-engineering:snakepolish` | Single-lens modernization assessment |
| `/python-engineering:modernpython` | Python-version/PEP modernization reference |
| `/python-engineering:shebangpython` | Shebang and PEP 723 validation/repair |
| `/python-engineering:python3-packaging` | Packaging and `pyproject.toml` |
| `/python-engineering:python3-publish-release-pipeline` | PyPI release automation |

Specialists for web, data/science, async, typing, testing, Typer/Rich, Textual, packaging and constrained stdlib-only environments are routed automatically.

## Agents

| Agent | Responsibility |
|---|---|
| `python-cli-architect` | Primary implementation agent; preserves project architecture and applies preferred defaults for new work |
| `adversarial-solution-design` | Independently traces the real change surface and challenges shallow plans |
| `python-cli-design-spec` | Architecture/contracts when material decisions require a design artifact |
| `python-pytest-architect` | Behavioral and property-based test design |
| `code-reviewer` | Bounded post-implementation review; broad audits route through `python-quality-audit` |
| `semantic-code-search` | Structural/pattern search across Python codebases |

## Existing projects

The plugin does not treat its preferences as permission for drive-by modernization.

It follows:

1. explicit user requirements and safety/security constraints;
2. repository Python floor, contracts, architecture, dependencies, CI and local conventions;
3. framework/library conventions;
4. plugin defaults.

Modernization becomes a deliberate task or an evidence-backed audit recommendation.

## Development

Load this checkout directly:

```bash
claude --plugin-dir ./plugins/python-engineering
```

Repository validation is defined by the repository's hooks and CI. Follow [the repository contribution guide](../../CONTRIBUTING.md) for development and submission requirements.

## License

MIT. See [LICENSE](../../LICENSE).
