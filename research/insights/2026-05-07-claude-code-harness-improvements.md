# Improvement Proposals: Claude Code Harness

**Research entry**: ./research/agent-frameworks/claude-code-harness.md
**Generated**: 2026-05-07
**Patterns assessed**: 9
**Backlog items created**: 6 (issues: #2180, #2181, #2182, #2183, #2184, #2185)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 1

---

## Improvement 1: PreToolUse Bash guardrail rules for destructive commands

**Source pattern**: Guardrail Engine R01-R13 — Key Features section. R01 denies `sudo`, R05 asks on `rm -rf`, R06 denies `git push --force`, R10 denies `--no-verify`/`--no-gpg-sign`, R11 denies `git reset --hard main/master`. Sub-10ms PreToolUse evaluation.
**Local system**: `plugins/development-harness/hooks/hooks.json`, `plugins/development-harness/hooks/block-context-direct-writes.cjs`
**Confidence**: High
**Impact**: High
**Backlog**: #2180 created

### Current state

The PreToolUse[Bash] hook chain in `plugins/development-harness/hooks/hooks.json` registers exactly one script: `block-context-direct-writes.cjs`. Reading lines 35-86 of that script confirms it only matches writes to `active-task-*.json` files (4 narrow regex patterns). It does not look for `sudo`, `git push --force`, `git push -f`, `rm -rf`, `--no-verify`, `--no-gpg-sign`, or `git reset --hard main/master`. `./.claude/CLAUDE.md` documents these constraints in the "Git Safety Protocol" section but those rules are advisory text consumed only by the orchestrator session — sub-agents spawned via `Agent` or `dh:task-worker` do not load `CLAUDE.md`, so no hook-level enforcement exists. A sub-agent issuing `git push --force` will execute it.

### Target state

A new hook script `plugins/development-harness/hooks/block-destructive-bash.cjs` registered as a PreToolUse[Bash] handler. Returns exit 2 (deny) for `sudo`, `git push --force*`, `--no-verify`, `--no-gpg-sign`, `git reset --hard (main|master)`. Returns ask-style exit for `rm -rf` and writes outside the project. Pattern set is data-driven via `destructive-bash-rules.json` so projects can extend without forking.

### Measurable signal

Run: `echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push --force origin main"}}' | node plugins/development-harness/hooks/block-destructive-bash.cjs` — exits 2 with stderr explaining the deny. `hooks/hooks.json` lists the new hook entry under PreToolUse[Bash].

---

## Improvement 2: Multi-perspective parallel review skill (Security/Performance/Quality/Accessibility)

**Source pattern**: Sub-Agents (3 Core) — Reviewer "performs 4-angle review (Security, Performance, Quality, Accessibility); reports verdict per perspective. Effort level: xhigh." Invoked via `/harness-review`.
**Local system**: `plugins/development-harness/skills/forensic-review/SKILL.md`, `plugins/development-harness/skills/code-review-*/`
**Confidence**: High
**Impact**: High
**Backlog**: #2181 created

### Current state

Local has language-scoped review skills (`code-review-python`, `code-review-typescript`, `code-review-cli`, `code-review-claude-skills`, `code-review-llm`, `code-review-nodejs`, `code-review-web`) — each invoked individually based on file type. `forensic-review/SKILL.md` runs `dh:code-reviewer` once per task as a single-pass review against AC. There is no orchestration that dispatches *perspective* reviewers (Security, Performance, Quality, Accessibility) in parallel against the same diff. Issue #1430 covers consolidation/dedup of multi-agent review findings but does not define the perspective scaffolding that produces the inputs.

### Target state

A new skill `plugins/development-harness/skills/multi-perspective-review/SKILL.md` that dispatches four parallel `dh:task-worker` agents via `TeamCreate("review-{slug}")`, each loaded with one of four perspective profiles: `reviewer-security`, `reviewer-performance`, `reviewer-quality`, `reviewer-accessibility`. Each returns a `{perspective, verdict, findings}` block. The skill collects all four and applies the #1430 consolidation pipeline.

### Measurable signal

`Skill(skill="dh:multi-perspective-review", args="--diff HEAD~1..HEAD")` produces output like `Security: APPROVE | Performance: REJECT (1) | Quality: APPROVE | Accessibility: SKIP`. Skill exits non-zero when any perspective rejects. `agent_profile/reviewer-{security,performance,quality,accessibility}.yaml` files exist.

---

## Improvement 3: Worker preflight self-check + structured worker-report contract

**Source pattern**: Sub-Agents (3 Core) — "Worker — Implements individual tasks from Plans.md; runs preflight self-check; awaits independent review verdict. Bound by contract in v4.3+: worker-report.v1 requires 5 self-review entries (source: CLAUDE.md)."
**Local system**: `plugins/development-harness/agents/task-worker.md`, `plugins/development-harness/skills/subagent-contract/SKILL.md`
**Confidence**: High
**Impact**: Medium
**Backlog**: #2182 created

### Current state

`task-worker.md` instructs the agent to claim, execute, and call `sam_task(action='state', status='complete')`. The `<concerns>` block read by `implement-feature/SKILL.md` step 4 is optional and unstructured — no schema requires the worker to attest to specific self-review checks. `dh:subagent-contract` describes a generic contract but defines no `worker-report.v1` schema. Issue #1857 addresses the *external* AC validation gate; this proposal addresses the *internal* worker self-attestation.

### Target state

`subagent-contract/SKILL.md` defines `worker-report.v1` with 5 required fields: `files_modified`, `tests_run`, `acceptance_criteria_attestation`, `deferred_work`, `risks_or_followups`. `task-worker.md` requires emitting `<worker_report>` JSON matching the schema before completion. `task_status_hook.py` parses the report and stores it as a `worker-report` artifact via `artifact_register`. Pydantic schema lives at `sam_schema/core/worker_report.py`.

### Measurable signal

Run a task via `dh:implement-feature`. Query `artifact_list(issue_number=N)` — output includes a `worker-report` entry. `artifact_read(N, "worker-report")` content contains all 5 v1 fields.

---

## Improvement 4: Advisor (weak-supervision) agent emitting PLAN/CORRECTION/STOP signals

**Source pattern**: Sub-Agents (3 Core) — "Advisor (Weak-Supervision Layer) — Optional consultative agent triggered on high-risk tasks, repeated failures, or plateau detection. Does not own final verdict; reports PLAN/CORRECTION/STOP signals to executor."
**Local system**: `plugins/development-harness/agents/`, existing circuit breaker proposal #929
**Confidence**: High
**Impact**: Medium
**Backlog**: #2183 created

### Current state

No consultative advisor agent exists in `plugins/development-harness/agents/`. `@dh:plan-validator` runs only at planning time. `@dh:contract-verification` runs only after task completion (too late to redirect). Issue #929 (circuit breaker) tracks consecutive tool failures and injects guidance text — a tool-level reflex, not a strategic supervisor that reads the agent's plan and emits semantic verdicts. No mechanism for plateau detection (worker stuck reading without writing) or high-risk-path guarding (writing to `**/auth/**`, `**/billing/**`, `*.lock`).

### Target state

A new `agents/advisor.md` and a `hooks/advisor-trigger.cjs` PostToolUse handler. Hook detects three triggers: repeated failure (same tool+target failed twice in last 10 events), plateau (5 consecutive Read/Grep without Edit/Write in 5 min), high-risk path (write target matches configurable patterns). On trigger, advisor runs and returns `{signal: PLAN|CORRECTION|STOP, reason, ...}`. Verdict appended to active-task context via `sam_active_task(action='update')`; worker reads on next turn. Advisor is consultative — worker may comply or log disagreement as a concern.

### Measurable signal

Run a task that fails the same Edit twice. Inspect `~/.dh/projects/{slug}/context/active-task-{session}.json` — contains `advisor_signals: [{signal: "CORRECTION", ts: ..., reason: ...}]`. Agent file `plugins/development-harness/agents/advisor.md` is registered.

---

## Improvement 5: dh doctor diagnostic command for plugin health and stale residue detection

**Source pattern**: Troubleshooting table — `bin/harness doctor` to diagnose hook installation; `bin/harness doctor --residue` auto-detects leftover references to deleted code from previous versions.
**Local system**: `plugins/development-harness/scripts/`, `plugins/development-harness/hooks/`
**Confidence**: High
**Impact**: Low
**Backlog**: #2184 created

### Current state

The plugin has no `dh doctor` script. When hooks fail (e.g., issue #950 — SubagentStop hook not marking SAM tasks complete), the user manually reads `hooks.json`, each hook script, MCP server connectivity, and state directory layout. There is no `--residue` mode that detects markdown links in `skills/**/*.md` pointing to deleted reference files, or skill-name strings in agent prompts referencing removed skills.

### Target state

`plugins/development-harness/scripts/dh_doctor.py` with five checks: hook wiring (every entry in `hooks.json` references an existing executable script), MCP server reachability (backlog + sam respond within 30s), state directory hygiene (expected subdirs present, no orphan active-task files >24h), plugin cache freshness (cache version matches source), residue detection (`--residue` flag walks markdown links and skill references). Exit 0 = all OK, 1 = any FAIL, 2 = WARN-only.

### Measurable signal

Run: `uv run --script plugins/development-harness/scripts/dh_doctor.py` — produces structured per-check report. With deliberately broken markdown link, `--residue` flag exits 1 and names the broken link.

---

## Improvement 6: Per-rule severity ladder (deny/ask/warn/allow) for Bash guardrails

**Source pattern**: Guardrail Engine table — R12 (direct push to main/master) "Ask by default (configurable: ask/deny/allow)"; R13 protected file edits "Warn". The Deny/Ask/Warn ladder lets projects tune severity per environment.
**Local system**: `plugins/development-harness/hooks/block-context-direct-writes.cjs` (template for future rule scripts)
**Confidence**: High
**Impact**: Low
**Backlog**: #2185 created

### Current state

`block-context-direct-writes.cjs` lines 122-124 produce only two outcomes: exit 2 (deny) or exit 0 (allow). No third state (warn-but-permit) and no fourth state (ask-with-default-deny). The script does not read any project-local config to decide its severity — the rule is hardcoded as deny. Same pattern would apply to any future PreToolUse Bash rule built off the same template (proposed in #2180).

### Target state

A config file `<project-root>/.dh/destructive-bash-rules.json` (with default at `plugins/development-harness/hooks/destructive-bash-rules.default.json`) declares per-rule action: `deny | ask | warn | allow`. `ask` returns Claude Code's permission-request structured stderr. `warn` returns stderr but exits 0. Rule scripts read the config, fall back to default when missing, apply the configured action per rule.

### Measurable signal

Create `.dh/destructive-bash-rules.json` with `"rm_rf": {"action": "warn"}`. Run: `echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf build/"}}' | node plugins/development-harness/hooks/block-destructive-bash.cjs` — exits 0 with warning stderr. Without the config override, returns the default `ask` exit shape.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Plans.md as Single Source of Truth + `harness sync` drift detection | Medium | The Harness pattern is `harness sync` to detect plan-vs-git drift. Local has plan-artifact-lifecycle.md (immutable vs mutable, divergence classification, annotation rules) — would need to read it to confirm whether automatic drift detection between plan artifact and current git state already exists. Without that read, cannot confidently say the gap is open. To raise confidence: read `plugins/development-harness/docs/plan-artifact-lifecycle.md` and `dispatch_stale_check` semantics. |
| Phase 0 Planning Discussion (Planner + Critic) before any code is written | Medium | Harness's `breezing` runs a planner-vs-critic phase before workers spawn. Local has `dh:rt-ica`, `dh:planner-rt-ica`, and `@dh:plan-validator` — these may already cover the Critic role. The exact gap (whether the orchestrator dispatches a paired Planner+Critic before approving the plan) requires reading rt-ica and plan-validator carefully. To raise confidence: compare RT-ICA output against a Planner-vs-Critic transcript, identify what dialectical critique the local pattern misses. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Go-native engine for sub-10ms PreToolUse latency | Architectural mismatch — local plugin is Python+Node and migrating to Go is out of scope for the agent-rule gap; the latency constraint matters less than the rule coverage gap (which is captured in #2180). |
| Codex CLI integration (delegate to OpenAI Codex in parallel) | Out of scope — repo is Claude-Code-focused; integrating a competing model runtime is a separate strategic decision, not a guardrail/skill improvement. |
| Cursor 2-Agent Mode (Cursor as PM, Claude Code as implementer) | Out of scope — repo does not target Cursor interop as a goal; the Plans.md sync between IDEs is not a problem the local system has. |
| Language lock-in via `CLAUDE_CODE_HARNESS_LANG=ja` (English/Japanese templates) | Out of scope — the local plugin is English-only by design; multi-language template machinery is not an identified gap. |
| harness-mem session memory companion | Already partially covered by `session-historian` skill (JSONL transcript search). The cross-session memory server pattern is its own architectural decision; not a small-delta improvement. |
| Scaffolder agent (project generation, v4.2+) | Already covered by `plugin-creator:plugin-creator` and `agent-creator` skills. |
