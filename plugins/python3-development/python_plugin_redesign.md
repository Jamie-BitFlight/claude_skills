# Python plugin rearchitecture and replacement design

## 1. Audit of the existing plugin

### Verdict

The current plugin is not one system. It is a stack of partially overlapping systems:

- a broad automatic router in `skills/python3-development/SKILL.md`
- a second broad router in `skills/specialist-skill-routing/SKILL.md`
- a manual orchestration layer in `skills/orchestrate/SKILL.md`
- routing embedded again inside multiple subagents, especially `agents/python-cli-architect.md`

That creates duplicated selection pressure, duplicated token spend, and inconsistent behavior depending on which entrypoint Claude touches first.

### Coherence issues

1. `orchestrate` is currently written like an automatic router, not a manual workflow command.
   - File: `skills/orchestrate/SKILL.md`
   - Problem: no `disable-model-invocation: true`, broad discovery-oriented description, and instructions that duplicate routing logic already present elsewhere.

2. The core Python skill is doing too many jobs.
   - File: `skills/python3-development/SKILL.md`
   - It mixes standing engineering defaults, library selection, workflow routing, reference indexing, command help, asset documentation, and quality-gate behavior.
   - Result: the first automatic load is too heavy and too broad.

3. `specialist-skill-routing` is a second router that exists largely because the primary router is overloaded.
   - File: `skills/specialist-skill-routing/SKILL.md`
   - It duplicates discovery work that should be handled by descriptions and narrower specialist skills.

4. Subagents preload and re-route the same domains again.
   - File: `agents/python-cli-architect.md`
   - The agent preloads `uv`, `python3-test-design`, `python-cli-architect`, `typer`, `rich`, and `typer-and-rich`, and then explicitly tells itself to activate `specialist-skill-routing` before starting.
   - This is routing recursion, not progressive disclosure.

5. The plugin still carries legacy process assumptions from an external workflow plugin.
   - Files: `README.md`, `CLAUDE.md`, `planning/*.md`, `agents/code-reviewer.md`, `skills/create-feature-task/SKILL.md`
   - There are many references to `development-harness`, `dh:*`, `sam`, and removed components. That makes the plugin depend on external structure even when the task is ordinary Python work.

### Redundancy

1. Multiple skills cover overlapping quality or review behavior:
   - `python3-review`
   - `comprehensive-test-review`
   - `analyze-test-failures`
   - `test-failure-mindset`
   - `stinkysnake`
   - `snakepolish`
   - `modernpython`

2. Multiple skills cover overlapping packaging and toolchain advice:
   - `python3-packaging`
   - `python3-publish-release-pipeline`
   - `uv`
   - `hatchling`
   - `pre-commit`
   - `toml-python`
   - `ty`

3. Multiple skills cover CLI development at different abstraction levels:
   - `python-cli-architect`
   - `typer`
   - `rich`
   - `typer-and-rich`
   - `textual`

The overlap is not just topical. It is structural. Several files repeat the same selection logic, the same tool recommendations, and the same project defaults.

### Stale references, placeholders, broken structure, dead weight

1. Placeholder content ships in a live skill.
   - File: `skills/mkdocs/SKILL.md`
   - Contains literal TODO blocks and scaffolding text.
   - This should not ship.

2. The plugin ships compiled Python bytecode.
   - Files: `scripts/__pycache__/*.pyc`
   - Dead weight and distribution noise.

3. There are many broken internal references.
   Representative examples from direct inspection:
   - `skills/python3-packaging/SKILL.md` references `python3-standards.md` through a path that does not exist.
   - `skills/semantic-code-search/SKILL.md` references `.mcp.json`, but the plugin has no `.mcp.json` at the root.
   - `skills/python3-development/SKILL.md` references `references/accessing_online_resources.md`, which is missing.
   - `skills/uv/SKILL.md` references multiple support files such as `quick-reference.md`, `configuration.md`, and `troubleshooting.md` that do not exist in its directory.
   - `skills/mkdocs/SKILL.md` references nonexistent helper files.

4. Several planning documents point to removed or nonexistent skills and agents.
   - Files: `planning/sse-gap-analysis.md`, `planning/sse-gap-analysis-verification.md`
   - These are historical internal notes, not runtime assets. They should not ship in the plugin.

5. The README is materially out of sync with the actual plugin shape.
   - It advertises 34 skills and a broader capability surface than the plugin can coherently support today.

### Conflicts with official best practices

1. Several SKILL.md files are far larger than the recommended size target.
   Examples from direct inspection:
   - `skills/uv/SKILL.md` about 1059 lines
   - `skills/pypi-readme-creator/SKILL.md` about 720 lines
   - `skills/pre-commit/SKILL.md` about 700 lines
   - `skills/async-python-patterns/SKILL.md` about 702 lines
   - `skills/toml-python/SKILL.md` about 631 lines
   - `skills/stinkysnake/SKILL.md` about 547 lines

2. The docs recommend keeping SKILL.md under 500 lines and moving detailed material into supporting files. The current plugin violates that repeatedly. It also says the description is the main selection signal and should carry most of the routing burden. The current plugin compensates for weak separation by adding more routers instead. citeturn384830view5turn384830view6

3. The docs distinguish automatic skills, manual entrypoint skills, background-only skills, and subagent execution. The current design blurs these roles, especially around `orchestrate` and the routing chain. `disable-model-invocation: true`, `user-invocable: false`, and `context: fork` exist precisely to make these distinctions explicit. citeturn384830view1turn384830view2turn384830view3

4. The docs recommend scripts for deterministic utility work because they are more reliable, cheaper, and more consistent than repeatedly prompting the model to reinvent checks. The current plugin describes many checks in prose that should be scripts or linter rules. citeturn384830view9

## 2. Target architecture

### Design principles

1. One automatic top-level Python router.
2. Manual commands are true manual commands.
3. Specialists are narrow and small.
4. Reference material is not invokable unless it drives a workflow.
5. Deterministic checks move to scripts.
6. Subagents preload only what they need.
7. The first automatic load establishes standing engineering defaults only.
8. Everything else is situational and loaded on demand.

### Hierarchy

#### A. Manual user entrypoint skills

These are slash-command workflows. They must not auto-load.

- `orchestrate`
- `review`
- `lint`
- `cleanup`
- `debug`

All five use `disable-model-invocation: true`.

#### B. One automatic top-level router

- `python-engineering`

This is the only broad automatic Python skill. It should load for general Python work and establish:

- strong Python engineering defaults
- SOLID as active design guidance
- testing and debugging standards
- modern module and tooling guidance
- code smells as investigation signals
- type coverage as a project health metric
- typed-boundary policy baseline

It should not act as a second slash workflow. It should load specialists when needed.

#### C. Automatic specialist skills

- `python-typing`
- `python-testing`
- `python-cli`
- `python-web`
- `python-data`
- `python-legacy`
- `python-packaging`

Each one should be concise and scenario-specific. These are the real routing targets. Their descriptions should do the selection work.

#### D. Subagent-preloaded skills

These are not user-facing and should be attached to subagents.

- `python-review-criteria`
- `python-debug-playbook`

They provide compact execution checklists for specialist agents without making the main skill graph heavier.

#### E. Reference material and assets

These are files, not invokable skills.

- `references/typing-policy.md`
- `references/version-typing-matrix.md`
- `references/tooling-defaults.md`
- `references/project-shapes.md`
- `references/testing-standards.md`
- `references/debugging-standards.md`
- `references/design-standards.md`
- `references/compatibility-lanes.md`
- `references/pydantic-boundaries.md`
- `references/hypothesis-boundaries.md`
- `assets/templates/...`

#### F. Deterministic scripts

- `scripts/detect_environment.py`
- `scripts/check_skill_refs.py`
- `scripts/check_manifest_consistency.py`
- `scripts/check_typing_boundaries.py`
- `scripts/check_plugin_layout.py`

### Default load versus on-demand load

#### First automatic load

`python-engineering`

It should do only four things:

1. establish universal Python defaults
2. classify project lane
3. choose typing strategy
4. load one or more narrow specialist skills only if needed

#### On-demand load

Load only the specialists relevant to the task:

- CLI task -> `python-cli`
- FastAPI, Django, Starlette, Flask, API server, auth, request validation -> `python-web`
- pandas, NumPy, notebooks, ETL, scientific Python -> `python-data`
- Python 3.10 constraints, stdlib-only requirement, vendor lock, legacy project -> `python-legacy`
- pyproject, build backend, release, packaging, dependency workflow -> `python-packaging`
- any design touching boundaries, validation, cast, type checker failures, model design -> `python-typing`
- TDD, pytest, fixtures, coverage, mocks, Hypothesis -> `python-testing`

### Progressive disclosure

1. `python-engineering` contains only standing defaults and routing logic.
2. Detailed lane-specific guidance lives in specialists.
3. Detailed matrices and examples live in reference files.
4. Scripts enforce what can be checked mechanically.

This follows the official skill design guidance: keep SKILL.md concise, let descriptions drive discovery, and push deep detail into separate files and scripts. citeturn384830view5turn384830view6turn384830view9

### Typing policy selection model

The model should never ask the user to choose a typing philosophy. It should detect the strongest valid lane from the repo state.

Decision order:

1. detect Python floor and target versions
2. detect third-party availability from `pyproject.toml`, lockfiles, imports, and installed project dependencies
3. detect whether the project is stdlib-only or constrained
4. choose the strongest valid typing lane
5. load `python-typing`
6. if tests touch boundaries and Hypothesis is present, also load `python-testing`

Selection priority:

1. project-constrained Python 3.10 stdlib-only lane
2. Python 3.11+ stdlib-only lane
3. Python 3.11+ with Pydantic lane
4. Python 3.11+ with Pydantic and Hypothesis lane
5. Python 3.12, 3.13, 3.14 lane refinements layered on top

## 3. Routing model

### The one automatic top-level Python router

- `python-engineering`

That is the only broad automatic router.

### Manual-entry-only skills

- `orchestrate`
- `review`
- `lint`
- `cleanup`
- `debug`

All of them should include `disable-model-invocation: true`. Per the skills docs, that also removes the description from normal model context, which is what you want for explicit workflow commands. citeturn384830view1

### What becomes reference files instead of skills

Downgrade these from invokable skills to reference material or scripts:

- `modernpython` -> `references/version-typing-matrix.md` and `references/design-standards.md`
- `test-failure-mindset` -> a section inside `python-testing`
- `typer-and-rich` -> absorbed into `python-cli`
- `python3-development-meta-docs` -> remove entirely
- `use-command-template` -> remove from this plugin; it is plugin-authoring meta work, not Python engineering runtime behavior
- `mkdocs`, `pypi-readme-creator`, `toml-python`, `hatchling`, `uv`, `ty`, `rich`, `typer`, `textual`, `async-python-patterns` -> convert to narrow reference files unless usage frequency justifies keeping one as a specialist. In this redesign, only `python-cli`, `python-packaging`, `python-typing`, and `python-testing` remain invokable because they map to active engineering tasks.

### Overlapping routers removed or consolidated

Remove or merge:

- remove `specialist-skill-routing`
- replace `python3-development` with `python-engineering`
- convert `orchestrate` into a pure manual workflow command
- remove routing instructions from subagents
- merge `stinkysnake`, `snakepolish`, and `modernpython` into `cleanup`, `lint`, and `python-engineering`
- merge test review and failure-analysis concepts into `review`, `debug`, and `python-testing`

## 4. Version-and-environment typing matrix

### Policy constants for all lanes

These apply everywhere:

- `Any`, broad `object`, and unchecked `cast()` are forbidden in internal code.
- They are allowed only at explicit system boundaries.
- Boundary code lives in dedicated validator, parser, adapter, or boundary modules.
- Boundary code validates immediately and returns typed objects.
- Raw payloads do not cross into the typed core.
- Boundary modules may be the only place with narrow lint exceptions for `Any`.

### Lane A: Python 3.10 constrained or stdlib-only

Use when:
- target runtime is Python 3.10
- third-party dependencies are unavailable or prohibited
- portability or system policy rules out Pydantic and Hypothesis

Approach:
- rely on stdlib `typing`, `dataclasses`, `TypedDict`, `Protocol`, `TypeGuard`, `NewType`, `Literal`
- use compatibility-safe patterns only
- boundary functions accept raw `dict[str, object]` or `Mapping[str, object]`
- validate with explicit runtime checks and convert to typed dataclasses or typed dicts
- property-based tests are optional only if Hypothesis is absent; otherwise use it

Boundary rule:
- explicit `parse_*`, `validate_*`, `*_from_raw` wrappers
- no unchecked `cast()` in core code

### Lane B: Python 3.11+ stdlib-only

Use when:
- project target is 3.11+
- no Pydantic dependency is available or desired

Approach:
- same as Lane A, plus newer stdlib typing features
- prefer `Self`, `assert_type`, `reveal_type` during development and refactors
- use native generics and `X | Y` unions everywhere

Python 3.11 specifically added `Self`, `assert_type()`, and `reveal_type()` which are directly useful for safer narrowing and refactoring. citeturn581424view0turn384830view1

### Lane C: Python 3.11+ with Pydantic

Use when:
- Pydantic is present or acceptable
- external boundaries are common
- request payloads, config payloads, tool output, or queue messages need validation

Approach:
- default to `BaseModel` for ingress contracts
- prefer strict mode where coercion would hide producer bugs
- use `TypeAdapter` for `list[T]`, `dict[str, T]`, unions, and annotated types
- use validators and serializers instead of ad hoc parsing branches

Pydantic explicitly supports type-driven validation, strict mode, validators, serializers, and `TypeAdapter` for annotated types. citeturn581424view0turn384830view9

### Lane D: Python 3.11+ with Hypothesis

Use when:
- Hypothesis is available
- boundaries, validators, serializers, parsers, or invariants matter enough to test generatively

Approach:
- property-test every boundary adapter
- use `from_type()` where possible to stay aligned with declared types
- type custom strategies with `SearchStrategy[T]`
- use Ghostwriter only to bootstrap, then refine manually

Hypothesis documents `from_type()`, typed strategies, and Ghostwriter for starter tests. citeturn581424view1

### Lane refinements by Python version

#### Python 3.11
- use `Self`
- use `assert_type()` in tests or type assertions
- use `reveal_type()` while removing casts or refactoring narrowings

#### Python 3.12
- use PEP 695 generic parameter syntax for new generic helpers
- use the `type` statement for explicit type aliases
- centralize raw-vs-validated aliases using the clearer alias syntax

#### Python 3.13
- use `TypeIs` for clearer custom narrowing helpers
- use `ReadOnly` in `TypedDict` fields that must not mutate after validation
- tighten post-validation payload invariants with read-only typed views

#### Python 3.14
- stop reading `__annotations__` directly in framework code
- use `annotationlib.get_annotations()` in infrastructure that must inspect annotations at runtime
- audit decorators, codegen, and metaprogramming for deferred annotation evaluation behavior

The Python release notes document those typing improvements across 3.11 to 3.14. citeturn581424view0turn384830view10

## 5. Concrete plugin redesign

## Proposed directory layout

```text
python-engineering/
├── .claude-plugin/
│   ├── plugin.json
│   └── validator.json
├── README.md
├── skills/
│   ├── python-engineering/
│   │   └── SKILL.md
│   ├── python-typing/
│   │   └── SKILL.md
│   ├── python-testing/
│   │   └── SKILL.md
│   ├── python-cli/
│   │   └── SKILL.md
│   ├── python-web/
│   │   └── SKILL.md
│   ├── python-data/
│   │   └── SKILL.md
│   ├── python-legacy/
│   │   └── SKILL.md
│   ├── python-packaging/
│   │   └── SKILL.md
│   ├── orchestrate/
│   │   └── SKILL.md
│   ├── review/
│   │   └── SKILL.md
│   ├── lint/
│   │   └── SKILL.md
│   ├── cleanup/
│   │   └── SKILL.md
│   ├── debug/
│   │   └── SKILL.md
│   ├── python-review-criteria/
│   │   └── SKILL.md
│   └── python-debug-playbook/
│       └── SKILL.md
├── agents/
│   ├── python-implementer.md
│   ├── python-reviewer.md
│   ├── python-test-architect.md
│   ├── python-cli-architect.md
│   └── python-debugger.md
├── references/
│   ├── compatibility-lanes.md
│   ├── debugging-standards.md
│   ├── design-standards.md
│   ├── hypothesis-boundaries.md
│   ├── project-shapes.md
│   ├── pydantic-boundaries.md
│   ├── testing-standards.md
│   ├── tooling-defaults.md
│   ├── typing-policy.md
│   └── version-typing-matrix.md
├── scripts/
│   ├── check_manifest_consistency.py
│   ├── check_plugin_layout.py
│   ├── check_skill_refs.py
│   ├── check_typing_boundaries.py
│   └── detect_environment.py
└── assets/
    └── templates/
        ├── pyproject.toml.j2
        ├── pre-commit-config.yaml
        └── boundary_module_example.py
```

### plugin.json

```json
{
  "name": "python-engineering",
  "description": "Python engineering workflows for modern application, library, and service development. Provides one automatic Python router, explicit review and debugging entrypoints, strict typed-boundary guidance, and specialist skills for CLI, web, data, legacy, testing, packaging, and typing-heavy work.",
  "version": "1.0.0",
  "author": {
    "name": "Jamie Nelson"
  }
}
```

### validator.json

```json
{
  "ignore": {
    "references": ["SK006"],
    "scripts": ["SK006"],
    "skills/orchestrate": ["SK006"],
    "skills/review": ["SK006"],
    "skills/lint": ["SK006"],
    "skills/cleanup": ["SK006"],
    "skills/debug": ["SK006"]
  }
}
```

## Skill files

### skills/python-engineering/SKILL.md
Role: the only automatic top-level Python router and default policy loader.

```markdown
---
name: python-engineering
description: Establishes default Python engineering guidance for implementation, refactoring, debugging, review, and design tasks. Use when working on Python codebases, modules, services, libraries, CLIs, tests, packaging, or typed boundaries. Loads narrower specialist skills only when the scenario requires them.
user-invocable: false
---

# Python Engineering

Apply these defaults for all Python work unless the repository clearly requires a different local convention:

- prefer clear module boundaries and small composable units
- use SOLID as active design guidance, not slogan text
- treat code smells as signals to investigate
- treat type coverage as a health metric, balanced against project constraints
- preserve operational clarity: clear failures, explicit configuration, debuggable behavior
- default target ecosystem is Python 3.11+
- Python 3.10 is a compatibility lane, not the preferred baseline

## Immediate classification

Before proposing or editing code:

1. detect Python version floor and target
2. detect project shape: CLI, web, data, library, service, legacy
3. detect typing lane from environment, dependencies, and constraints
4. load only the specialist skills needed for the task

## Always load when relevant

- load `python-typing` for any task involving data boundaries, schema design, type errors, casts, models, or validation
- load `python-testing` for TDD, pytest, fixtures, property tests, boundary tests, or coverage work
- load `python-cli` for CLI apps, scripts, terminal UX, or command design
- load `python-web` for HTTP servers, APIs, request validation, auth, or web frameworks
- load `python-data` for notebooks, ETL, pandas, NumPy, scientific code, or data pipelines
- load `python-legacy` for Python 3.10 constraints, stdlib-only work, dependency restrictions, or compatibility-first repos
- load `python-packaging` for pyproject, release, build, toolchain, dependency, or packaging tasks

## Standing design rules

- unknown-shape external data belongs only at explicit boundaries
- boundary modules must validate immediately and return typed objects
- internal code should not pass raw payloads around
- prefer deterministic checks and scripts over repeated model judgment for policy enforcement
- match existing project tools when already standardized, unless asked to modernize deliberately

## References

Read these only when needed:

- `../../references/typing-policy.md`
- `../../references/version-typing-matrix.md`
- `../../references/design-standards.md`
- `../../references/testing-standards.md`
- `../../references/tooling-defaults.md`
- `../../references/project-shapes.md`
```

### skills/python-typing/SKILL.md
Role: adaptive typed-boundary and validation policy specialist.

```markdown
---
name: python-typing
description: Selects and applies the strongest valid Python typing strategy for the current project. Use when designing models, validating external data, addressing type checker failures, reducing Any usage, defining boundaries, or choosing between stdlib typing, Pydantic, and Hypothesis-based boundary testing.
user-invocable: false
---

# Python Typing

Choose the strongest valid lane automatically. Do not ask the user to pick a typing philosophy.

## Required policy

- forbid `Any`, broad `object`, and unchecked `cast()` in normal internal code
- allow them only at explicit boundaries where unknown-shape data enters the system
- isolate boundary code in dedicated validator, parser, adapter, or boundary modules
- validate immediately and return strongly typed internal objects
- do not let raw payloads cross into the typed core
- allow narrow lint exceptions for `Any` only in approved boundary modules

## Lane selection

1. Python 3.10 constrained or stdlib-only
   - use only compatibility-safe stdlib typing features
   - prefer dataclasses, TypedDict, Protocol, Literal, TypeGuard, NewType
   - validate with explicit runtime checks in dedicated boundary wrappers

2. Python 3.11+ stdlib-only
   - use modern stdlib typing features supported by the interpreter
   - use `Self`, `assert_type`, and `reveal_type` where useful during refactoring

3. Python 3.11+ with Pydantic
   - use Pydantic models for ingress contracts
   - prefer strict mode where coercion would hide upstream errors
   - use `TypeAdapter` for annotated types that do not need full models

4. Python 3.11+ with Hypothesis
   - property-test boundaries, validators, parsers, and invariants
   - prefer `from_type()` where practical

5. Python 3.12+
   - use clearer generic syntax and explicit type aliases where project style allows

6. Python 3.13+
   - use `TypeIs` and `ReadOnly` where they simplify boundary safety or narrowing

7. Python 3.14+
   - keep annotation-reading infrastructure compatible with deferred annotation evaluation

## Boundary implementation standard

Use dedicated wrappers named like:

- `parse_*`
- `validate_*`
- `decode_*`
- `coerce_*`
- `*_from_raw`

Boundary modules should return typed objects only.

## References

- `../../references/typing-policy.md`
- `../../references/version-typing-matrix.md`
- `../../references/pydantic-boundaries.md`
- `../../references/hypothesis-boundaries.md`
- `../../references/compatibility-lanes.md`
```

### skills/python-testing/SKILL.md
Role: TDD, pytest, and boundary-testing specialist.

```markdown
---
name: python-testing
description: Guides TDD, pytest architecture, debugging failing tests, fixture design, and property-based testing for Python projects. Use when writing tests first, expanding coverage, validating boundaries, designing fixtures, diagnosing flaky or failing tests, or using Hypothesis with validators and parsers.
user-invocable: false
---

# Python Testing

Apply these defaults:

- prefer TDD when adding behavior or fixing bugs with a clear specification gap
- investigate failing tests before changing them
- treat tests as executable specifications, not obstacles
- keep tests small, isolated, explicit, and easy to debug

## Standard expectations

- use pytest as the default test runner unless the repo already standardizes elsewhere
- write clear fixture boundaries and avoid hidden shared state
- cover boundary validators and adapters directly
- use property-based tests when Hypothesis is available and the boundary or invariant benefits from generative coverage
- keep deterministic examples for known regressions even when Hypothesis is present

## Load references as needed

- `../../references/testing-standards.md`
- `../../references/hypothesis-boundaries.md`
- `../../references/debugging-standards.md`

## Testing decisions

- TDD flow: write or refine the failing test, implement the smallest valid change, rerun checks, then refactor
- boundary validation flow: example tests first, then property-based tests when available
- flaky test flow: isolate environment, time, order, randomness, and I/O assumptions before changing assertions
```

### skills/python-cli/SKILL.md
Role: CLI and script development specialist.

```markdown
---
name: python-cli
description: Guides Python CLI and script development, including command design, terminal output, user-facing ergonomics, script boundaries, and operational behavior. Use when building command-line tools, structured scripts, Typer-based CLIs, or terminal-facing developer utilities.
user-invocable: false
---

# Python CLI

Apply these defaults for CLI work:

- design commands around stable user tasks, not internal module structure
- keep parsing, validation, domain logic, and rendering separate
- validate external input at boundaries before passing into the core
- prefer predictable stdout and stderr behavior and explicit exit codes
- keep terminal formatting secondary to correctness and scriptability

## Framework selection

- if the project already uses Typer, follow that style
- if the task is a simple script or constrained environment, keep dependencies minimal
- do not introduce terminal UI dependencies without a real need

## Load references only when required

- `../../references/project-shapes.md`
- `../../references/design-standards.md`
- `../../references/tooling-defaults.md`
```

### skills/python-web/SKILL.md
Role: web and API specialist.

```markdown
---
name: python-web
description: Guides Python web and API development with strong request boundaries, typed validation, and maintainable service design. Use when building or reviewing HTTP endpoints, request and response models, authentication flows, service layers, or framework-based web applications.
user-invocable: false
---

# Python Web

For web work:

- separate transport concerns from domain logic
- validate request and response boundaries explicitly
- avoid leaking framework objects into the domain layer
- prefer typed request and response models
- push serialization and validation to boundary modules or framework adapters

## Typical loads

- load `python-typing` for any request or payload modeling
- load `python-testing` for endpoint tests, auth flows, or boundary behavior

## References

- `../../references/design-standards.md`
- `../../references/typing-policy.md`
- `../../references/testing-standards.md`
```

### skills/python-data/SKILL.md
Role: data and scientific Python specialist.

```markdown
---
name: python-data
description: Guides Python data, ETL, analysis, and scientific workflows with maintainable module boundaries and explicit validation at ingress points. Use when working with pandas, NumPy, notebooks, pipelines, tabular data ingestion, or scientific processing code.
user-invocable: false
---

# Python Data

For data-oriented work:

- keep ingestion, cleaning, transformation, and presentation separate
- validate schema assumptions at the first stable ingress point
- avoid passing loosely typed dataframes or records through unrelated layers without documenting invariants
- move reusable notebook logic into tested modules when it becomes durable behavior

## Typical loads

- load `python-typing` for record schemas, parsers, adapters, and typed transformations
- load `python-testing` for parser behavior, edge cases, and regression protection

## References

- `../../references/project-shapes.md`
- `../../references/typing-policy.md`
- `../../references/testing-standards.md`
```

### skills/python-legacy/SKILL.md
Role: constrained-environment and compatibility specialist.

```markdown
---
name: python-legacy
description: Guides Python work in constrained, compatibility-first, or dependency-restricted environments. Use when the target is Python 3.10, stdlib-only, enterprise-restricted, legacy, or otherwise limited by interpreter version, dependency policy, or operational constraints.
user-invocable: false
---

# Python Legacy

Treat constraints as first-class requirements.

## Required behavior

- preserve compatibility before applying modernization patterns
- prefer stdlib solutions when dependency policy is restrictive
- choose typing features that are valid for the project floor
- make boundary wrappers explicit when Pydantic or other helpers are unavailable
- avoid recommending tools or syntax that exceed the project lane

## References

- `../../references/compatibility-lanes.md`
- `../../references/version-typing-matrix.md`
- `../../references/tooling-defaults.md`
```

### skills/python-packaging/SKILL.md
Role: build, dependency, and packaging specialist.

```markdown
---
name: python-packaging
description: Guides Python packaging, build, dependency, environment, and release work. Use when editing pyproject.toml, choosing build backends, managing dependencies, structuring tool configuration, or preparing release and CI workflows.
user-invocable: false
---

# Python Packaging

Apply these defaults:

- keep packaging decisions aligned with the repository's actual distribution and deployment needs
- do not introduce tool churn without a concrete gain
- prefer one coherent dependency and build workflow
- keep type-checking, linting, test, and packaging configuration discoverable and centralized

## References

- `../../references/tooling-defaults.md`
- `../../references/design-standards.md`
- `../../references/compatibility-lanes.md`
```

### skills/orchestrate/SKILL.md
Role: manual workflow entrypoint for multi-step Python engineering tasks.

```markdown
---
name: orchestrate
description: Orchestrates a multi-step Python engineering workflow from a user-supplied task description.
disable-model-invocation: true
argument-hint: [task description]
---

# Orchestrate

Use this as a manual workflow command for complex Python work.

## Inputs

Task: $ARGUMENTS

If no argument is supplied, derive the task from the active conversation.

## Workflow

1. classify the task: feature, refactor, review, debug, packaging, migration, or cleanup
2. identify project lane: CLI, web, data, library, service, or legacy
3. identify typing lane from repository constraints
4. choose the minimum set of specialist skills needed
5. produce a concise execution plan
6. execute or delegate in the smallest coherent units
7. run deterministic checks before declaring completion

## Delegation rules

- use specialist skills for guidance
- use subagents only when the task has separable parallelizable work or needs isolated analysis
- do not duplicate routing already handled by `python-engineering`
- do not preload unrelated specialists
```

### skills/review/SKILL.md
Role: manual workflow entrypoint for review.

```markdown
---
name: review
description: Reviews Python changes for design quality, typed-boundary compliance, testing adequacy, and maintainability.
disable-model-invocation: true
argument-hint: [path or scope]
---

# Review

Review the requested Python scope with these priorities:

1. correctness and boundary safety
2. design clarity and maintainability
3. test quality and debugging ergonomics
4. type health and avoidable escape hatches
5. operational clarity

Always apply `python-review-criteria` and load any needed specialists based on the code under review.
```

### skills/lint/SKILL.md
Role: manual workflow entrypoint for deterministic code-quality checks.

```markdown
---
name: lint
description: Runs or guides deterministic Python quality checks, including linting, typing, test, and policy validation workflows.
disable-model-invocation: true
argument-hint: [path or scope]
---

# Lint

For the requested scope:

1. detect the repo's configured checkers
2. run deterministic checks that already exist in the project
3. run plugin policy checks when appropriate
4. report failures grouped by category
5. fix only when the user asked for fixing, otherwise review and explain

Prefer scripts and project checkers over prose-only analysis.
```

### skills/cleanup/SKILL.md
Role: manual workflow entrypoint for structured cleanup and modernization.

```markdown
---
name: cleanup
description: Improves Python code quality through focused cleanup, smell investigation, modernization, and typed-boundary hardening.
disable-model-invocation: true
argument-hint: [path or scope]
---

# Cleanup

Use this command for controlled cleanup work.

## Goals

- remove duplication and ambiguous ownership
- investigate code smells instead of suppressing them
- improve typed boundaries and reduce escape hatches
- modernize only within the project's compatibility lane
- preserve behavior unless explicitly changing it

Load `python-typing`, `python-testing`, and any domain specialist required by the target scope.
```

### skills/debug/SKILL.md
Role: manual workflow entrypoint for debugging.

```markdown
---
name: debug
description: Debugs Python failures using a structured investigation workflow focused on reproduction, boundary assumptions, and root-cause isolation.
disable-model-invocation: true
argument-hint: [symptom, error, or path]
---

# Debug

Use a structured debugging flow:

1. restate the observed symptom
2. identify the smallest reproducible scope
3. isolate environment, input, state, and concurrency assumptions
4. inspect boundary validation and conversion points early
5. distinguish implementation bugs from test bugs
6. verify the fix with deterministic checks

Always apply `python-debug-playbook` and load any domain specialist needed for the failing area.
```

### skills/python-review-criteria/SKILL.md
Role: subagent-preloaded compact review checklist.

```markdown
---
name: python-review-criteria
description: Supplies compact review criteria for Python code review subagents. Use when performing design, maintainability, testing, boundary, or typing review.
user-invocable: false
---

# Python Review Criteria

Check for:

- clear module responsibilities
- typed boundaries for external data
- minimal and justified use of escape hatches
- tests that match behavior and edge cases
- design choices that reduce hidden coupling
- operational clarity in failures and configuration
- changes that respect the repository's compatibility lane
```

### skills/python-debug-playbook/SKILL.md
Role: subagent-preloaded compact debugging checklist.

```markdown
---
name: python-debug-playbook
description: Supplies a compact debugging workflow for Python debugging subagents. Use when isolating failures, reproducing bugs, or validating fixes.
user-invocable: false
---

# Python Debug Playbook

Debug in this order:

1. reproduce
2. narrow scope
3. inspect boundaries and invariants
4. verify assumptions with direct evidence
5. fix the smallest real cause
6. rerun deterministic checks
7. document any remaining uncertainty or follow-up risk
```

## Removed, merged, renamed, or downgraded components

### Removed entirely

- `specialist-skill-routing` - redundant router
- `python3-development-meta-docs` - dead index pattern
- `use-command-template` - plugin-authoring meta feature, not runtime Python engineering
- `mkdocs` - placeholder and out of scope for a coherent Python engineering core
- planning documents under `planning/` - historical notes, not runtime assets
- `scripts/__pycache__/` - dead binary artifacts

### Renamed or replaced

- `python3-development` -> `python-engineering`
- `python3-review` -> `review`
- `python3-bug` -> `debug`
- `python3-packaging` + `python3-publish-release-pipeline` -> `python-packaging`
- `python3-test-design` + pieces of `comprehensive-test-review` + `analyze-test-failures` -> `python-testing`
- `python-cli-architect` skill -> `python-cli`

### Merged into references

- `modernpython`
- `test-failure-mindset`
- `rich`
- `typer`
- `typer-and-rich`
- `textual`
- `uv`
- `ty`
- `pre-commit`
- `hatchling`
- `toml-python`
- `pypi-readme-creator`
- `async-python-patterns`
- `shebangpython`

These are useful knowledge domains, but they do not each need to remain separate invokable runtime skills in the base Python plugin. They become reference files or templates unless usage data later proves they deserve promotion.

## 6. Deterministic enforcement recommendations

Implement these as scripts or linter rules, not prose.

### A. Typing-boundary policy check

Script: `scripts/check_typing_boundaries.py`

Checks:
- forbid `Any` outside approved boundary modules
- flag `cast(` outside approved boundary modules
- flag raw `dict[str, Any]` or equivalent in internal service and domain modules
- require approved naming convention for modules containing `Any`
- optionally require every approved boundary module to expose typed return values

Suggested behavior:
- parse Python AST
- allow configurable approved module globs such as `**/*_boundary.py`, `**/*_validators.py`, `**/*_adapters.py`, `**/*_parsers.py`
- report exact file and line violations

### B. Environment detection

Script: `scripts/detect_environment.py`

Checks:
- Python version floor and target from `pyproject.toml`, `.python-version`, CI config, tool config
- presence of Pydantic and Hypothesis in dependency metadata
- presence of project type checker and linter
- project shape hints from imports and entrypoints

Output:
- machine-readable JSON lane selection

### C. Stale reference check

Script: `scripts/check_skill_refs.py`

Checks:
- every local file reference inside SKILL.md exists
- every referenced skill name exists
- every agent-preloaded skill exists
- every README or docs path exists

This would have caught many current broken references.

### D. Manifest consistency check

Script: `scripts/check_manifest_consistency.py`

Checks:
- skill directories match skill names where required
- plugin README counts and listed skills match actual plugin contents
- validator ignore targets correspond to real paths
- no orphan skills or agents are referenced from nowhere

### E. Plugin layout check

Script: `scripts/check_plugin_layout.py`

Checks:
- no `__pycache__` or compiled artifacts ship
- no placeholder TODO blocks remain in shipped SKILL.md files
- no SKILL.md exceeds the configured line budget without explicit approval
- no manual entrypoint omits `disable-model-invocation: true`
- no background-only skill is accidentally user-invocable

### F. Project-integrated enforcement

Also recommend:
- ruff rules for import hygiene and modernization
- configured type checker for the repo's chosen lane
- optional pre-commit hook that runs the plugin scripts on the plugin itself

## 7. Migration plan

### Phase 1: Add new architecture beside old structure

1. create the new `python-engineering` plugin directory structure
2. add new skills, references, and scripts
3. keep old plugin installable during transition
4. add compatibility notes in README

### Phase 2: Convert core routing

1. introduce `python-engineering`
2. convert `orchestrate` to manual-only
3. remove `specialist-skill-routing` from all agents and skills
4. update agents to preload only the new compact specialists they actually need

### Phase 3: Downgrade oversized skills

1. move long-form guidance from old skills into `references/`
2. leave thin compatibility shim skills temporarily where breakage would be costly
3. each shim should say it is deprecated and forward to the new skill or reference

Compatibility shims worth keeping briefly:
- `python3-development` -> tells the system to use `python-engineering`
- `python3-review` -> tells the system to use `review`
- `python3-bug` -> tells the system to use `debug`
- `python3-packaging` -> tells the system to use `python-packaging`

Each shim should be under 20 lines and removed after one release cycle.

### Phase 4: Remove dead weight

1. delete placeholder `mkdocs`
2. delete `planning/`
3. delete `__pycache__/`
4. delete broken or obsolete references
5. remove README claims that no longer reflect the plugin

### Phase 5: Turn checks on

1. wire `check_skill_refs.py`, `check_manifest_consistency.py`, and `check_plugin_layout.py` into CI
2. wire `check_typing_boundaries.py` into plugin CI and optionally project CI
3. fail releases if placeholder content, broken refs, or routing regressions reappear

## Final recommendation

Do not preserve the current structure. Flatten it.

The replacement should be:
- one automatic Python router
- five explicit manual workflow commands
- seven narrow specialists
- two compact subagent-only support skills
- references for deep material
- scripts for enforcement

That gives Claude one coherent Python engineering system instead of a maze of overlapping prompts.
