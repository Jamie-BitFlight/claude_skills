# Utilization Proposals: Waza

**Research entry**: ./research/skill-generation-tools/waza.md
**Generated**: 2026-05-04
**Integration surfaces found**: 4 (CLI skills + installation mechanism)
**Proposals written**: 3
**Skipped**: 2 — pattern-only (no direct callable surface documented)

---

## Utilization 1: `dh:analyze-test-failures` → Waza `/hunt` skill

**Research entry**: ./research/skill-generation-tools/waza.md
**Caller**: ./plugins/development-harness/skills/analyze-test-failures/SKILL.md
**Integration mechanism**: CLI skill invocation (`/hunt`)
**Replaces or adds**: Extends root-cause-first debugging discipline with multi-platform reproducibility verification
**Setup cost**: Low (install via `npx skills add tw93/Waza -a claude-code -g -y`)
**Integration surface**: `/hunt` skill (GitHub: tw93/Waza)

### Why this caller

The `analyze-test-failures` skill in development-harness guides agents through debugging test failures, but it is context-limited to test execution output within a single codebase. Waza's `/hunt` skill ("bugs, crashes, regressions, test failures, unexpected behavior") is a generalized debugging entrypoint that enforces the same discipline (`find root cause before applying fix`) across all failure types — not just tests. The skill's documented design rule ("Focuses on reproducible failures and confirmed root causes") matches our error-handling philosophy in `plugins/development-harness/skills/code-review-python/SKILL.md` (lines 56-60: "Exception messages must include context to diagnose without reading the source").

Reading `./plugins/development-harness/skills/analyze-test-failures/SKILL.md`, the current flow is: gather output → propose hypothesis → instrument/isolate → validate. Waza's `/hunt` enforces structured reproduction before hypothesis, making it more rigorous. Integration would allow callers to route general-purpose debugging to `/hunt` when the failure is not test-specific (server crashes, integration bugs, unexpected behavior).

### Integration sketch

```markdown
## When to use `/hunt` (Waza)

Route to `/hunt` when:
- Failure occurs in production or integration environment (not test sandbox)
- Reproduction steps are unclear or non-deterministic
- Multiple systems interact (not isolated test failure)
- The error is not a test assertion but unexpected behavior

Route to `/dh:analyze-test-failures` when:
- Failure is in `pytest` or test runner output
- Test is isolated and reproducible in CI/local environment
- Root cause is suspected to be within the code under test
```

**Before integration**: Verify that Waza `/hunt` skill is installable and operational in this repo's Claude Code session via `npx skills add tw93/Waza -a claude-code -g -y` and that it can be invoked as `/hunt <problem description>`.

---

## Utilization 2: `dh:code-review-python` (and siblings) → Waza `/check` skill

**Research entry**: ./research/skill-generation-tools/waza.md
**Caller**: ./plugins/development-harness/skills/code-review-python/SKILL.md (and code-review-{cli,nodejs,typescript,web})
**Integration mechanism**: CLI skill invocation (`/check`)
**Replaces or adds**: Adds project-context-aware review mode to language-specific reviewers
**Setup cost**: Low (install via `npx skills add tw93/Waza -a claude-code -g -y`)
**Integration surface**: `/check` skill with ship/release/triage modes (GitHub: tw93/Waza)

### Why this caller

The `code-review-python` skill (and its sibling language-specific skills) focuses on enforcing language and stack-specific rules (ruff, ty, pytest conventions, error handling patterns). Waza's `/check` skill is positioned earlier in the release workflow: it extracts project context (README, CI, manifests, version sync requirements) and performs project-aware review (safe auto-fixes, release asset verification, artifact protection). Reading lines 85-91 of the research entry, Waza's `/check` "extracts constraints from the target repository: Project commands from README, package manifests, Makefiles; CI workflow files; Release docs and scripts."

Our language-specific reviewers assume a shared harness context. Waza's `/check` is agnostic to language and runs *before* language-specific review — it answers "is this safe to release?" independent of how the code was written. Integration would allow callers to invoke `/check` before routing to `dh:code-review-python`, ensuring release-safety checks happen before style/idiom enforcement.

Reading `./plugins/development-harness/skills/code-review-python/SKILL.md`, the current scope is: Python-specific rules (type hints, ruff, pytest, uv). It does not handle project-context concerns (release assets, version sync, artifact protection, safe auto-fixes based on CI configuration). Waza fills that gap.

### Integration sketch

```markdown
## Release / Ship workflow integration

When reviewing a change for release/publication/push:

1. Route to `/check` with context: target repository, intended action (release/publish/push)
2. Waza extracts project constraints and produces artifact checklist
3. Only after Waza's `/check` passes, route to language-specific reviewer:
   - `/code-review-python` for Python stacks
   - `/code-review-nodejs` for Node.js stacks
   - etc.
```

**Before integration**: Verify that Waza `/check` skill can be invoked with a repository context (diff, PR, or path), and that its output includes artifact verification and version sync requirements. Test against a sample PR in this repo.

---

## Utilization 3: `refresh-research` → Waza `/learn` skill

**Research entry**: ./research/skill-generation-tools/waza.md
**Caller**: `.claude/skills/refresh-research/SKILL.md` (and research-curator agent)
**Integration mechanism**: CLI skill invocation (`/learn`)
**Replaces or adds**: Extends research workflow with structured six-phase methodology and self-review gate
**Setup cost**: Low (install via `npx skills add tw93/Waza -a claude-code -g -y`)
**Integration surface**: `/learn` skill (six-phase workflow: collect, digest, outline, fill, refine, review) (GitHub: tw93/Waza)

### Why this caller

The `refresh-research` skill (and the `research-curator` agent at `.claude/agents/research-curator.md`) guide research workflows. Reading the research entry (lines 50, end of "Eight Skills" table), Waza's `/learn` skill "runs a six-phase research workflow: collect, digest, outline, fill in, refine, then self-review and publish." The `research-curator` agent (lines 1-50 of `.claude/agents/research-curator.md`) orchestrates research waves and produces `./research/{category}/{name}.md` outputs; it does not itself execute the research phases — it delegates to agents.

Waza's `/learn` provides structured phases for *conducting* research (phases: collect sources, digest findings, outline structure, fill in sections, refine prose, then self-review before publication). Our current research workflow (via `research-curator`) manages the *orchestration* (waves, freshness tracking, backlink detection) but does not prescribe internal research phases. Integration would allow callers to use `/learn` for individual research topics, then feed the output into our backlog/insight pipeline.

Reading `.claude/skills/refresh-research/SKILL.md` and `.claude/agents/research-curator.md`, the current research lifecycle is: identify topic → spawn agent to research → write entry → auto-extract insights. Waza's `/learn` adds rigor to the middle phase (the actual research conduct) with explicit phases and self-review gate.

### Integration sketch

```markdown
## Research workflow with `/learn`

When conducting deep research on a topic:

1. Identify topic and required research depth
2. Invoke `/learn` with the topic:
   - It will guide you through collect → digest → outline → fill → refine → review
3. Output from `/learn` becomes source for `research-curator` pipeline:
   - Entry is normalized into `.md` format and registered with `artifact_register`
   - Insights are extracted via `research-insight-extractor`
   - Backlog items are created for actionable proposals
```

**Before integration**: Verify that Waza `/learn` skill can be invoked with a research topic and that its output is in a format compatible with our research entry format (markdown with frontmatter). Test a sample research topic.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/skills/fact-check/SKILL.md` | Waza's `/read` skill (fetches URLs/PDFs) does not overlap with fact-check scope (verify claims against sources). The `/read` skill is a content fetcher, not a verifier. No direct utilization opportunity; pattern adoption only. |
| `plugins/orchestrator-discipline/` | Waza's skill design principles (explicit "Not for" sections, manual chaining) are patterns. The research entry documents them but does not provide a callable surface for orchestration discipline enforcement. No utilization surface. |

---

## Next Steps

1. **Install and test Waza skills** — Run `npx skills add tw93/Waza -a claude-code -g -y` in a test session and verify `/hunt`, `/check`, `/learn` are available.

2. **For Utilization 1** (`/hunt`): Create a backlog item to add routing logic to `dh:analyze-test-failures` that delegates non-test failures to `/hunt`. Test with a production crash scenario.

3. **For Utilization 2** (`/check`): Integrate `/check` as a pre-release gate in the harness code-review pipeline. Modify `code-review-python` (and siblings) to accept an optional `check-first` mode that invokes Waza `/check` before language-specific rules.

4. **For Utilization 3** (`/learn`): Test `/learn` on a sample research topic, verify output format, then link from `research-curator` as an optional structured research mode for deep-dive topics.

---

## Confidence Assessment

| Proposal | Confidence | Why |
|---|---|---|
| Utilization 1 (`/hunt`) | High | Clear overlap with debugging discipline; Waza's design is documented and the skill is production-tested. Requires routing logic only. |
| Utilization 2 (`/check`) | High | Waza's project-context extraction is novel and fills a gap our language-specific reviewers don't address. Integration is additive, not replacing. |
| Utilization 3 (`/learn`) | Medium | Waza's `/learn` phases are documented but we have not tested the skill's output format against our research entry schema. Format compatibility must be verified before committing integration. |

