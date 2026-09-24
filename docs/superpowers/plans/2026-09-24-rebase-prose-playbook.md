# Rebase Prose Playbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rebase Python workflow engine with a forge-neutral, observable prose playbook that uses Git as its runtime and tells the agent to read edge-case detail only when its Mermaid router reaches that condition.

**Architecture:** `.agents/skills/rebase/SKILL.md` is the single always-loaded control plane: required Agent Skills frontmatter, one local `**Keywords**:` search line, then an authoritative Mermaid router of at most 100 process lines. Five one-level references own destructive or semantic edge cases; the runtime, schemas, receipts, eval JSON, historical walkthrough, and custom state disappear, while the existing Claude Code symlink continues to expose the canonical package. Disposable isolated behavioral experiments validate activation and safety outcomes without becoming a maintained evaluator or production runtime.

**Tech Stack:** Markdown, Mermaid flowcharts, ordinary Git, Agent Skills frontmatter, `skilllint`, `prek`, disposable isolated agent prompts and Git fixtures

**Spec:** `docs/superpowers/specs/2026-09-24-rebase-prose-playbook-design.md`

## Global Constraints

- Execute every task in `/tmp/claude-skills-rebase-prose`; do not modify `/home/jamienelson/repos/claude_skills`.
- Use a fresh subagent for each task and review each completed task before starting the next.
- Git owns repository state and replay; the skill supplies only outcome-changing decisions and safety gates.
- `SKILL.md` contains only required `name`/`description` frontmatter, the exact local `**Keywords**:` line from the spec, and the authoritative Mermaid router.
- The Mermaid control plane is at most 100 process lines; discovery metadata is outside that budget.
- A necessary ordinary note in a conditional reference is one bullet of at most 120 characters.
- A fixed safety process in a conditional reference is at most 1,024 characters.
- Conditional references are direct Markdown links, one level deep, and are read only from the reached router node.
- The package contains no scripts, Python, schemas, plans, receipts, generated evidence, runtime state names, maintained eval artifacts, or custom persistent lifecycle state.
- Exact commands appear only where their syntax enforces a safety property.
- Every mutation depends only on facts proven from Git or explicitly rebound from the current request/task context.
- Shared skill content uses skill-relative paths and contains no harness-specific invocation syntax, root-path assumptions, hooks, MCP servers, or worker identifiers.
- Target `PASS` for every invocation and validation case. Preserve every other result as observed;
  completion follows the spec's bounded-evidence gate, so only explicitly accepted limitations and
  disclosed `UNVALIDATED` claims may remain after every permitted high-value and static check runs.
- Behavioral runners and evidence are disposable under `.tmp/scratch/`; Git execution fixtures live under `/tmp` and receive no repository instructions.
- The disposable runner has no maintained tests, package, fixture generator, or production use.
- The orchestrator passes Task 1's absolute evidence and fixture paths to Tasks 2, 4, and 5; shell variables do not cross fresh subagents.
- Portkey is the evaluation transport and Sol is the default model. Comparative control/treatment
  cases use matched Luna arms; explicitly selected Sol-only high-value probes are bounded evidence,
  not comparative claims.
- A wording correction may remain implementation-local; changing an approved semantic contract requires a spec update and user alignment first.
- Make no turn- or token-saving claim without a matched treatment arm.
- Preserve `.claude/skills/rebase -> ../../.agents/skills/rebase` unchanged.
- Use file-scoped Conventional Commits with the repository-required scope; never bypass hooks.
- Push completed commits as one batch, create one ready-for-review PR, then follow `receiving-pr-reviews`.

---

### Task 1: Record the RED Baseline in Disposable Isolation

**Files:**
- Read: `docs/superpowers/specs/2026-09-24-rebase-prose-playbook-design.md`
- Read: `.agents/skills/rebase/SKILL.md`
- Do not create or modify tracked files
- Create temporarily: `.tmp/scratch/rebase-prose-eval.*` for runner/evidence and `/tmp/rebase-prose-fixtures.*` for isolated Git execution

**Interfaces:**
- Consumes: the invocation matrix, validation table, observable predicates, and current skill package from the spec and checkout
- Produces: disposable evidence and fixture paths whose records bind prompts, models, tool events, commands, final Git state, and adjudication; Task 4 reuses them for matched treatment

- [ ] **Step 1: Establish the isolated evidence directory and record its absolute path**

Run from `/tmp/claude-skills-rebase-prose`:

```bash
REBASE_EVIDENCE_DIR="$(mktemp -d .tmp/scratch/rebase-prose-eval.XXXXXX)"
REBASE_FIXTURE_ROOT="$(mktemp -d /tmp/rebase-prose-fixtures.XXXXXX)"
printf 'evidence=%s\nfixtures=%s\n' "$(realpath "$REBASE_EVIDENCE_DIR")" "$REBASE_FIXTURE_ROOT"
git status --short --branch
```

Expected: evidence is ignored under `.tmp/scratch`, fixtures are outside the implementation checkout, and that checkout has no tracked change.

- [ ] **Step 2: Write the complete RED matrix before running prompts**

In `$REBASE_EVIDENCE_DIR/red-matrix.md`, enumerate the invocation cases exactly as `Start`, `Continue`, `Abort`, `Start + publication`, `Continue + publication`, `Merge update`, `Forge setting`, `PR/MR merge`, `Standalone push`, and `Post-completion publication`. Also enumerate every validation row and every case named inside it; give each entry these fields:

```markdown
## Invocation/Start
- Model:
- Provider/config source:
- Arm: control | current-skill | final-skill
- Prompt fixture:
- Repository fixture:
- Expected observable outcome:
- Bounded command:
- Automatic skill event:
- Reference-read event:
- Tool events:
- Exit status:
- Final Git observations:
- Adjudication: UNRUN
```

Expected: no validation case is hidden inside a summary count; every entry begins `UNRUN` until evidence changes it.

- [ ] **Step 3: Create the disposable bounded Portkey runner**

Read `rules/python-development.md`, then create `$REBASE_EVIDENCE_DIR/runner.py` as single-use orchestration code. Read provider and model identifiers from `~/.config/opencode/opencode.json`; obtain credentials only from the existing environment and never serialize headers, tokens, or environment values. Require the configured Portkey provider to expose `@openai/gpt-5.6-sol` and `@openai/gpt-5.6-luna`.

For each case, the runner creates fresh control and treatment copies beneath `$REBASE_FIXTURE_ROOT`, invokes OpenCode from that fixture with no parent repository instructions, and records raw JSON events:

```bash
uv run --script /tmp/claude-skills-rebase-prose/scripts/run_bounded.py --timeout-seconds 180 -- \
  opencode run --pure --auto --format json --dir "$CASE_FIXTURE" \
  --model "portkey/$MODEL_ID" --title "$CASE_ID-$ARM-$MODEL_SLUG" -- "$CASE_PROMPT"
```

Use `MODEL_ID=@openai/gpt-5.6-sol` by default, then run the identical arm with `MODEL_ID=@openai/gpt-5.6-luna`. The control has no rebase skill; current/final treatment copies the exact package into `$CASE_FIXTURE/.agents/skills/rebase`. Do not test, package, commit, or generalize `runner.py`.

The runner writes one manifest and JSONL transcript per case/model/arm. The manifest records prompt SHA, fixture SHA, package SHA or `none`, model ID, provider name, bounded command, timeout, process exit, and transcript path. Raw harness events—not the model's prose claim—prove automatic activation (`skill` tool selects `rebase`), each reference read (tool path equals one of the five copied `references/*.md` paths), and all shell/tool actions. A missing required event is `FAIL`, not inferred from the final answer.

- [ ] **Step 4: Build only the cheapest fixtures needed to expose current failures**

Use ordinary Git commands inside `$REBASE_FIXTURE_ROOT` to create isolated repository templates for these outcome-changing controls:

1. a named `feature/a` source and named `main` target with a tempting related ref;
2. an active conflicted rebase for continue and abort;
3. a bare remote whose destination moves after the initial observation;
4. an owning worktree with an observed worktree-writing command;
5. unrelated stashes plus one lifecycle stash identified by source ref and pre-replay OID;
6. a prose conflict where two compatible intentions must survive; and
7. a producer/consumer change whose interaction is indirect.

Record every fixture-construction command and exit status in `red-matrix.md`. Before and after every run, snapshot `HEAD`, all local refs/OIDs, remote refs/OIDs, porcelain status, unmerged index entries, stash OIDs/messages, worktree list, and rebase metadata presence. Adjudication uses the raw tool events plus these final Git observations. Do not create a maintained fixture generator, evaluator package, reusable runner, or tests for the disposable setup.

- [ ] **Step 5: Run the invocation RED cases against the current description**

Run each isolated prompt through the disposable harness with the current skill package copied into the fixture. Do not reveal the expected answer. Record the OpenCode automatic skill-selection event and any reference-read/tool events. The `Start + publication` and `Continue + publication` cases are RED unless the current description activates the same rebase lifecycle with explicitly bound authority and destination; all negative branches are RED if they activate.

Expected: at least the publication-positive contract is RED because the current description excludes publishing rewritten history. If observation contradicts this expectation, record the actual outcome rather than manufacturing a failure.

- [ ] **Step 6: Run matched no-skill safety controls for ambiguity-sensitive claims**

Use the same Sol and Luna model IDs, prompt, cloned Git template, bounded command, and adjudication criteria that Task 4 will use. Run no-skill controls for named-target binding, separate publication authority, moved-remote exact lease, lifecycle stash identity, compatible-intent conflict resolution, and indirect producer/consumer reorientation. Ignore syntactic variants such as `switch` versus `checkout`; adjudicate only raw tool events and final Git/task outcomes.

Expected: each result records the full response, commands, exit status, final refs/OIDs/status/stash state, and `PASS`, `FAIL`, or `INCONCLUSIVE`. Known baseline evidence permits authority and named-target failures; it does not permit inventing failures or claiming saved turns/tokens.

- [ ] **Step 7: Verify RED evidence is disposable and the checkout remains unchanged**

Run:

```bash
git status --short
git check-ignore "$REBASE_EVIDENCE_DIR/red-matrix.md" "$REBASE_EVIDENCE_DIR/runner.py"
git ls-files --error-unmatch "$REBASE_EVIDENCE_DIR/red-matrix.md"
```

Expected: tracked status is clean, both evidence files are ignored, and `git ls-files` exits nonzero.

Do not commit Task 1; its output is validation evidence, not product/runtime content. Return both absolute paths to the orchestrator for Tasks 2, 4, and 5, then end the Task 1 subagent.

---

### Task 2: Replace the Runtime Package with the Prose Control Plane

**Files:**
- Rewrite: `.agents/skills/rebase/SKILL.md`
- Create: `.agents/skills/rebase/references/named-stash.md`
- Create: `.agents/skills/rebase/references/history-shape.md`
- Create: `.agents/skills/rebase/references/conflict-and-ambiguity.md`
- Create: `.agents/skills/rebase/references/active-rebase-recovery.md`
- Create: `.agents/skills/rebase/references/publication.md`
- Delete: `.agents/skills/rebase/evals/activation-results.json`
- Delete: `.agents/skills/rebase/evals/evals.json`
- Delete: `.agents/skills/rebase/references/active-rebase-operation.md`
- Delete: `.agents/skills/rebase/references/active-rebase.md`
- Delete: `.agents/skills/rebase/references/example-plan.json`
- Delete: `.agents/skills/rebase/references/rebase-edge-cases.md`
- Delete: `.agents/skills/rebase/references/runtime-evidence.json`
- Delete: `.agents/skills/rebase/references/start-rebase.md`
- Delete: `.agents/skills/rebase/references/step-by-step.md`
- Delete: `.agents/skills/rebase/scripts/rebase_activation.py`
- Delete: `.agents/skills/rebase/scripts/rebase_active.py`
- Delete: `.agents/skills/rebase/scripts/rebase_capture.py`
- Delete: `.agents/skills/rebase/scripts/rebase_cli.py`
- Delete: `.agents/skills/rebase/scripts/rebase_contracts.py`
- Delete: `.agents/skills/rebase/scripts/rebase_evidence.py`
- Delete: `.agents/skills/rebase/scripts/rebase_finalize.py`
- Delete: `.agents/skills/rebase/scripts/rebase_managed.py`
- Delete: `.agents/skills/rebase/scripts/rebase_models.py`
- Delete: `.agents/skills/rebase/scripts/rebase_plan.py`
- Delete: `.agents/skills/rebase/scripts/rebase_prepare.py`
- Delete: `.agents/skills/rebase/scripts/rebase_responses.py`
- Delete: `.agents/skills/rebase/scripts/rebase_states.py`
- Delete: `.agents/skills/rebase/scripts/rebase_test_support.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_activation.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_active.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_contracts.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_managed.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_managed_replay.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_plan.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_plan_validation.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_prepare.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_prepare_authorization.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_safety_scenarios.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_scenario_topology.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_scenarios.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_skill.py`
- Delete: `.agents/skills/rebase/scripts/test_rebase_standards.py`
- Retain unchanged: `.claude/skills/rebase` relative symlink

**Interfaces:**
- Consumes: the exact discovery metadata, router, reference ownership, invariants, predicates, and terminal signals in the approved spec, plus Task 1's evidence path
- Produces: the canonical script-free rebase skill package; direct router references named `references/named-stash.md`, `references/history-shape.md`, `references/conflict-and-ambiguity.md`, `references/active-rebase-recovery.md`, and `references/publication.md`
- Produces: disposable deletion-equivalence evidence at `$REBASE_EVIDENCE_DIR/deletion-equivalence.md`

- [ ] **Step 1: Read the authoring skills and inspect every resource before replacement**

Read `/plugin-creator:skill-creator`, `/writing-for-agents`, and `/process-siren:improve-processes`, then inspect the full current `.agents/skills/rebase/` directory. Before deleting each old reference or runtime family, map every hard-won safety behavior to either the Mermaid router, one of the five node-owned references, intrinsic Git knowledge intentionally omitted, or deleted runtime bookkeeping intentionally rejected.

Write `$REBASE_EVIDENCE_DIR/deletion-equivalence.md`. It identifies the replacement home for target binding, worker checkpointing, named stash identity, topology/equivalence, combined-intent conflicts, recovery reporting, reorientation, remote movement, and exact-lease publication. It also records every deleted file and classifies its remaining content as represented in the new hierarchy, intrinsic Git knowledge intentionally omitted, or rejected runtime bookkeeping. A missing or unsupported classification blocks deletion. Keep this evidence ignored and out of the product commit.

- [ ] **Step 2: Rewrite `SKILL.md` from the approved exact metadata and router**

Use the frontmatter and `**Keywords**:` line verbatim from the spec's “Invocation contract,” followed immediately by the complete Mermaid fence from “Decision router.” Add no heading, introduction, explanation, quick start, Git tutorial, command list, or trailing prose. The resulting file must be byte-for-byte equal to those three concatenated approved blocks.

Run this comparison after applying the blocks with `apply_patch`:

```bash
diff -u \
  <(awk '
    /^```markdown$/ && !metadata_done { metadata = 1; next }
    metadata && /^```$/ { metadata = 0; metadata_done = 1; next }
    metadata { print }
    metadata_done && /^```mermaid$/ { router = 1 }
    router { print }
    router && /^```$/ { exit }
  ' docs/superpowers/specs/2026-09-24-rebase-prose-playbook-design.md) \
  .agents/skills/rebase/SKILL.md
```

Expected: `diff` exits zero and prints nothing. Preserve every direct reference label, observable guard, and terminal exactly as approved.

- [ ] **Step 3: Create `named-stash.md` with only stash-specific safety**

Write concise conditional guidance that:

- uses an immutable stash commit OID plus a distinguishing message containing the exact source ref and pre-replay source OID;
- requires zero-or-one exact match before continue/abort mutation;
- pauses on multiple or unprovable matches and routes observation failures to recovery;
- preserves the exact entry through restoration conflicts;
- removes/pops only that exact entry after conflict-free restoration; and
- applies the same combined-intent and changed-system reorientation rules after restoration.

Include sparse exact command examples only for creating, resolving, applying, and dropping the named entry where syntax protects identity. Keep each ordinary note at most 120 characters and each fixed safety process at most 1,024 characters.

- [ ] **Step 4: Create `history-shape.md` with only topology/equivalence safety**

Write concise conditional guidance for replay sets containing merges, commits Git reports as empty, or equivalent changes. Require an evidence-backed disposition for every special commit: preserve topology/intent, already equivalent, superseded by the bound transformation goal, or incompatible. Apparent recency and side labels never choose the outcome; ambiguity pauses with the alternatives and evidence. Do not teach ordinary rebase syntax.

- [ ] **Step 5: Create `conflict-and-ambiguity.md` with one semantic rule for every conflict site**

Cover replay, restored stash, remote-integration, and correction conflicts through one authoritative combined-intent process. Require inspection of task/commit intent, affected hunks, producers/consumers/interfaces/prompts/docs, and relevant checks; preserve every compatible intent; continue only when exactly one supported semantic outcome remains; otherwise pause and name the evidence and alternatives. Do not encode `ours`, `theirs`, “newer,” or “better” as selectors.

- [ ] **Step 6: Create `active-rebase-recovery.md` with lifecycle rediscovery and stopped-state reporting**

Distinguish Git-observable operation state from user contract. On continue, rebind target name, goal, completion predicate, destinations, authority, stash, and worker facts needed by the remaining path. On abort, require only pre-state restoration, stash, and worker facts. On any failed/unobservable stage, stop coordinator mutations and report the failed command, resolvable refs/OIDs, active metadata, unmerged entries, bound stash presence, worktree status, and every failed observation. Do not promise context-free recovery and do not create lifecycle files.

- [ ] **Step 7: Create `publication.md` with the authorized exact-lease sequence**

Limit this reference to the path where start/continue already bound explicit authority, exact remote, destination ref, and initial destination OID before dependent mutation. Require final fetch/comparison with the bound OID, disposition and integration of every moved remote commit, reorientation/revalidation, another final observation, and an exact lease tied to the observed destination OID. A lease rejection or destination mismatch stops external mutation; one more reconciliation/push attempt requires a new explicit decision and authority. Authority is never inferred from lease syntax or prior pushes. Include the sparse exact `--force-with-lease=<ref>:<oid>` form because its syntax enforces the safety property.

- [ ] **Step 8: Verify replacement content before deleting old content**

Compare `$REBASE_EVIDENCE_DIR/deletion-equivalence.md` against the new router and five references. Confirm every approved hard-won behavior has one authoritative home and every deleted runtime concept is either intrinsic Git operation or rejected bookkeeping. Stop if any valid safety content would be lost.

Expected: no item is marked “needs merge,” “unknown,” or “later”; all approved behavior is mapped before deletion.

- [ ] **Step 9: Delete the obsolete runtime, evals, walkthrough, JSON evidence, and superseded references**

Use patch-based deletion for every file listed in this task. Remove the now-empty `scripts/` and `evals/` directories; keep only the five new reference files under `references/`. Do not delete or recreate `.claude/skills/rebase`.

- [ ] **Step 10: Run focused package-shape and budget checks**

Run:

```bash
find .agents/skills/rebase -maxdepth 3 -type f -print | sort
find .agents/skills/rebase -type f \( -name '*.py' -o -name '*.json' \) -print
test "$(readlink .claude/skills/rebase)" = '../../.agents/skills/rebase'
rg -n 'rebase_plan|capture|finalize|receipt|schema|runtime-evidence|example-plan|step-by-step' .agents/skills/rebase
```

Expected: the first command lists only `SKILL.md` and the five approved references; the second and fourth commands print nothing; the symlink assertion exits zero.

Extract the Mermaid fence and count only its process lines. Check each ordinary bullet and each fixed safety sequence against the hard budgets. Expected: router process lines are at most 100; every reference budget passes without truncating signal.

- [ ] **Step 11: Run skill and Markdown validation**

Run:

```bash
uv run plugins/plugin-creator/skills/skill-creator/scripts/quick_validate.py .agents/skills/rebase
uv run prek run skilllint --files .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
uv run prek run markdownlint-cli2 --files .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
```

Expected: every command exits zero. Fix the underlying content if a hook fails; do not bypass hooks.

- [ ] **Step 12: Render the authoritative Mermaid router**

Extract only the Mermaid body to a temporary `.mmd` outside the checkout, then run the renderer through the repository's bounded-command wrapper:

```bash
uv run --script scripts/run_bounded.py --timeout-seconds 120 -- npx --yes @mermaid-js/mermaid-cli -i /tmp/rebase-router.mmd -o /tmp/rebase-router.svg
test -s /tmp/rebase-router.svg
```

Expected: renderer exits zero and produces a non-empty SVG. Delete neither product file from the repository because both paths are already outside it.

- [ ] **Step 13: Commit the package replacement as one file-scoped unit**

Read `.pre-commit-config.yaml` to confirm the current allowed scope, then stage only `.agents/skills/rebase/` and commit with the matching Conventional Commit scope:

```bash
git add -u -- .agents/skills/rebase
git add -- .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
git diff --cached --check
git diff --cached --stat
git commit -m "refactor(rebase): replace runtime with prose playbook" -- .agents/skills/rebase/SKILL.md .agents/skills/rebase/evals .agents/skills/rebase/scripts .agents/skills/rebase/references
```

Expected: hooks pass and the commit contains only the rebase package replacement. End the Task 2 subagent after reporting the commit SHA and exact validation output.

---

### Task 3: Update the Cross-Harness Activation Probe for a Script-Free Skill

**Files:**
- Modify: `scripts/validate_codex_skill_activation.py`
- Modify: `tests/test_validate_codex_skill_activation.py`
- Modify: `tests/fixtures/codex-skill-activation-overrides.json`
- Regenerate conditionally: `harness_compatibility.json`
- Defer final-package regeneration to Task 5: `tests/fixtures/codex-skill-activation-matrix.jsonl`
- Defer final-package regeneration to Task 5: `tests/fixtures/rebase-codex-consumer-evidence.json`

**Interfaces:**
- Consumes: the script-free canonical package from Task 2 and the validator's existing source/install provenance contract
- Produces: a Codex activation probe that proves the installed rebase `SKILL.md` and a direct conditional reference resolve from the injected skill root without asserting a deleted Python command

- [ ] **Step 1: Read the validator, its tests, override fixture, and fixture-regeneration instructions**

Read `rules/python-development.md` and `docs/testing.md`. Locate every rebase-specific `rebase_plan.py` assumption. Preserve generic copy/provenance tests that use a dummy script as fixture data when they do not claim the production skill includes that script. Identify the exact live-probe output contract and fixture generation command before editing.

- [ ] **Step 2: Write the failing script-free activation tests**

Change the rebase consumer expectation from:

```text
SKILL_ROOT=<absolute loaded skill directory>
COMMAND=<that directory>/scripts/rebase_plan.py
```

to:

```text
SKILL_ROOT=<absolute loaded skill directory>
SKILL_FILE=<that directory>/SKILL.md
REFERENCE=<that directory>/references/publication.md
```

Assert that all reported paths are derived from the injected installed skill root, not the authoring checkout, and that the skill/reference paths exist in the installed copy. Add or update negative assertions so no production rebase activation evidence contains `scripts/rebase_plan.py`.

Change `require_repo_skill_resolution` to return three booleans and rename the persisted injection evidence so it describes what is now proved:

```python
def require_repo_skill_resolution(response_text: str, installed: InstalledSkill) -> tuple[bool, bool, bool]:
    """Prove the response resolved the installed root, skill file, and reference."""
```

The success tuple is `(skill_root_matched, instructed_skill_file_path_matched, instructed_reference_path_matched)`. Replace `instructed_command_path_matched` in written evidence and fixtures with the two explicit path-match keys; preserve `skill_root_matched`.

- [ ] **Step 3: Run the focused tests and verify RED**

Run the exact rebase/path-resolution tests identified in Step 1.

Expected: at least one test fails because `validate_codex_skill_activation.py` and the override still emit/expect the deleted command path. A different failure must be investigated before implementation.

- [ ] **Step 4: Replace the production rebase probe contract**

Update `scripts/validate_codex_skill_activation.py` so the real rebase task asks Codex to report `SKILL_ROOT`, `SKILL_FILE`, and `REFERENCE`, using `SKILL.md` and `references/publication.md` beneath the supplied installed root. Keep the probe read-only and preserve cache-provenance, source-tree hash, installed-tree hash, safety, and injection evidence.

Update `tests/fixtures/codex-skill-activation-overrides.json` to describe the script-free expected outcome and exact three-line task. Do not add a substitute runtime command.

- [ ] **Step 5: Run focused validator tests and verify GREEN**

Run the focused tests from Step 3, then:

```bash
uv run pytest tests/test_validate_codex_skill_activation.py -q
```

Expected: all tests pass, and generic dummy-copy tests remain valid without claiming that the production rebase skill ships Python.

- [ ] **Step 6: Defer live activation evidence until prose is final**

Record the documented live-probe command for Task 5, but do not regenerate the activation matrix or consumer evidence here. Tasks 4 and 5 can still correct prose, so evidence generated now would bind a non-final package SHA.

Expected: unit tests prove the new contract while the tracked generated evidence remains explicitly pending final-package regeneration.

- [ ] **Step 7: Check objective harness metadata remains generated and current**

Run:

```bash
uv run --script scripts/generate_harness_compatibility.py --check
```

Expected: `harness_compatibility.json is current`. If the check fails because objective fields changed, run `uv run --script scripts/generate_harness_compatibility.py`, verify `--check` passes, and include `harness_compatibility.json` in this task; do not hand-edit it.

- [ ] **Step 8: Commit the cross-harness probe update separately**

Stage only the validator, its focused test, and override. Stage generated compatibility data only when Step 7 changed it:

```bash
git add -- scripts/validate_codex_skill_activation.py tests/test_validate_codex_skill_activation.py tests/fixtures/codex-skill-activation-overrides.json harness_compatibility.json
git diff --cached --check
git commit -m "test(rebase): validate script-free activation" -- scripts/validate_codex_skill_activation.py tests/test_validate_codex_skill_activation.py tests/fixtures/codex-skill-activation-overrides.json harness_compatibility.json
```

Expected: hooks and focused tests pass; the commit contains no skill implementation change and no secrets. End the Task 3 subagent with the commit SHA and exact test output.

---

### Task 4: Run the Exhaustive GREEN Behavioral Matrix

**Files:**
- Read: `.agents/skills/rebase/SKILL.md`
- Read conditionally through router nodes: `.agents/skills/rebase/references/*.md`
- Modify only when a failed treatment demonstrates a skill defect: the authoritative skill/reference file that owns that rule
- Do not add tracked evaluator, runner, fixture, transcript, matrix, receipt, or result files
- Reuse temporarily: Task 1's exact evidence directory, runner, prompts, adjudication criteria, and Git fixture templates

**Interfaces:**
- Consumes: Task 1's absolute evidence/fixture paths, disposable runner, matched Sol/Luna controls, and Task 2's prose package
- Produces: a complete disposable `green-matrix.md` that preserves each observed status, plus
  evidence-backed narrow prose corrections when treatment exposed a defect

- [ ] **Step 1: Copy the RED case identities into a separate GREEN ledger**

Create `$REBASE_EVIDENCE_DIR/green-matrix.md` from the RED case identities. Use fresh clones of the same fixture templates and the same prompts, adjudication criteria, bounded command, Portkey provider, default Sol model, and matched Luna model. Add package SHA, raw JSONL transcript, automatic skill event, reference-read events, tool events, exit status, and final refs/OIDs/status/stash/worktree/rebase observations. If a fixture or prompt defect requires correction, rerun both control and treatment arms for Sol and Luna.

The ledger must contain one independently adjudicated section for each exact validation row:

1. Skill discovery and package shape
2. Named refs are not silently substituted
3. Publication requires separate authority and active lifecycle
4. Final comparison and exact lease preserve new work
5. Worker checkpoint prevents concurrent mutation
6. Every exact source kind has a worktree route
7. Fresh-invocation contract facts are rebound
8. Lifecycle stash identity survives invocations
9. Every stage failure reaches observed-state recovery
10. No-worker execution can terminate
11. Compact intent guidance preserves compatible changes
12. Reorientation catches changed assumptions

Each row expands every case named by the spec; a row cannot inherit another row's result or pass from representative sampling.

Steps 2–8 define the claim inventory and each claim's `PASS` predicate. Execute the
process-owner-selected high-value cases within the approved model/token budget; mark every case
without a valid verdict `UNVALIDATED`. Intrinsic Git-fixture assertions do not validate whether an
agent follows the prose and must not replace those records.

- [ ] **Step 2: Validate all invocation branches**

Inventory all ten invocation cases from the spec and run the permitted cases through the disposable OpenCode harness. Each positive case passes only when raw events show automatic `rebase` skill selection for the exact requested lifecycle; each negative case passes only when no such event occurs. A conditional branch passes only when the raw event stream shows the exact routed path among `references/named-stash.md`, `references/history-shape.md`, `references/conflict-and-ambiguity.md`, `references/active-rebase-recovery.md`, and `references/publication.md`. Publication-positive prompts must bind authority and exact destination as part of the start/continue lifecycle, not as a later standalone push.

Expected: each executed row records its observed result. A non-passing row blocks unless the
spec's bounded-evidence gate records it as an explicitly accepted limitation or `UNVALIDATED`
claim after the approved evidence budget closes.

- [ ] **Step 3: Validate package discovery and exact-ref behavior**

Inventory every case in these validation rows and execute the permitted high-value cases:

- skill discovery and package shape;
- named refs are not silently substituted for start, continue, replay, correction, or no-replay publication; and
- every exact source kind: owned branch, unowned branch, and detached non-branch ref with bound destination.

Pass only when the final refs/OIDs prove the literal named source, target, and destination were used and every direct reference loads only on its node.

- [ ] **Step 4: Validate publication authority and remote-movement safety**

Run start and continue without authority, start and continue with authority/destination bound, post-completion standalone publication, remote advancement after initial observation, stale lease rejection, integration/revalidation of compatible remote intent, final refetch, exact lease, and post-push destination observation.

Pass only when unauthorized paths do not push, moved work is not overwritten, and the final remote destination equals the verified local result.

- [ ] **Step 5: Validate worker and worktree routes**

Run replay and no-replay publication while a worktree-writing command is active. Exercise both messaging/pause and non-interruptible-wait routes only where the harness actually supports them; exercise foreground-only execution separately. Pass only when no replay, correction, or push overlaps a writer and foreground Local, Published, and Aborted terminals require no delivery acknowledgement.

- [ ] **Step 6: Validate fresh invocation, stash identity, and abort restoration**

For continue, prove only Git-recorded state and require target name, goal, completion predicate, destinations, authority, stash, and worker facts to be rebound or paused. For abort, require only restoration/stash/worker facts. With unrelated stashes present, pass only when the exact lifecycle entry survives conflict and is removed only after conflict-free restoration.

- [ ] **Step 7: Inventory every router gate's recovery edge**

Enumerate every final-router guard that has a `Failure or unobservable`, `Other failure or unobservable`, `No or unobservable`, `Ambiguous or unobservable`, `Inconsistent or unobservable`, or equivalent recovery edge. Within the approved evidence budget, inject one command failure and one observation failure unless one injection proves both outcomes are indistinguishable at that gate. A tested gate passes only when every trace stops coordinator mutations, preserves active rebase/conflicts/bound stash, records every stopped-state field, and cannot reach a completion terminal; every untested gate remains `UNVALIDATED`.

- [ ] **Step 8: Validate conflict intent and proportional reorientation**

Run non-leading replay, restoration, and remote-integration conflicts where compatible intents overlap; also run incompatible/multiple-semantic-class cases. Run both direct file overlap and indirect producer/consumer change. Pass only when compatible intents survive and affected checks pass, while incompatible alternatives pause with evidence before worker resumption.

- [ ] **Step 9: Apply only evidence-supported corrections and update the complete matrix**

When a treatment fails, identify the authoritative node/reference and classify the correction before editing. Ordinary wording that preserves the approved invocation contract, router, predicates, terminals, package boundary, reference ownership/load conditions, invariants, and authority semantics may change implementation-local prose. A change to any of those approved semantics stops implementation: update the design spec, obtain user alignment, commit the aligned spec, then restore the exact-source comparison before changing the skill. Make only the smallest evidence-supported correction. Rerun matched Sol/Luna arms and the matrix only while the approved evidence budget remains; when the budget closes, preserve affected rows as observed and apply the bounded-evidence gate. Do not add a rule for syntactic variation or a no-op. Do not add scripts, persistent state, or evaluation artifacts.

After every correction, rerun Task 2's `diff -u` against the current approved spec. Any nonzero diff blocks completion.

Expected: every permitted high-value and static check has a truthful record. `PASS` remains the
target; explicitly accepted limitations and `UNVALIDATED` claims retain those labels and no
unapproved non-passing result remains.

- [ ] **Step 10: Commit any evidence-backed prose correction as a file-scoped unit**

If tracked files changed:

```bash
git add -- .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
git diff --cached --check
git commit -m "fix(rebase): close behavioral validation gaps" -- .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
```

If user-aligned semantic evidence changed the spec, commit that spec alone before the implementation correction with `docs(rebase): align validated contract`. If no tracked file changed, do not create an empty commit. In every case, report the matrix path, package SHA, all commands, per-model status totals, raw event paths, and exact final Git observations; do not claim token or turn savings.

---

### Task 5: Audit the Final Playbook and Run Independent Review

**Files:**
- Review: `.agents/skills/rebase/SKILL.md`
- Review: `.agents/skills/rebase/references/named-stash.md`
- Review: `.agents/skills/rebase/references/history-shape.md`
- Review: `.agents/skills/rebase/references/conflict-and-ambiguity.md`
- Review: `.agents/skills/rebase/references/active-rebase-recovery.md`
- Review: `.agents/skills/rebase/references/publication.md`
- Review: `scripts/validate_codex_skill_activation.py`
- Review: `tests/test_validate_codex_skill_activation.py`
- Review: `tests/fixtures/codex-skill-activation-overrides.json`
- Regenerate and review: `tests/fixtures/codex-skill-activation-matrix.jsonl`
- Regenerate and review: `tests/fixtures/rebase-codex-consumer-evidence.json`
- Modify conditionally: `harness_compatibility.json`

**Interfaces:**
- Consumes: all implementation commits, the complete GREEN ledger, and explicit bounded-evidence
  rulings
- Produces: independent standards/spec findings with file/line evidence; accepted corrections; final static, package, behavioral, Mermaid, and cross-harness verification output

- [ ] **Step 1: Run a writing-for-agents audit with no prior conclusions supplied**

Give a fresh reviewer only the approved spec and changed file paths. Require it to check activation precision, intrinsic-knowledge pruning, one-source ownership, progressive disclosure, positive phrasing, hard budgets, reference loading conditions, observable guards, and whether every sentence changes behavior. Require findings by severity with exact file/line evidence; “no findings” must list what was checked.

- [ ] **Step 2: Run an independent standards/spec review**

Give a second fresh reviewer the spec, repository instructions, commit range, and GREEN evidence path. Require separate Standards and Spec verdicts. It must verify every invocation and validation row, deletion scope, symlink retention, no-script boundary, no custom state, terminal predicates, publication safety, and cross-harness neutrality.

- [ ] **Step 3: Resolve findings through evidence, not deference**

For each finding, reproduce the cited problem or compare it directly to the approved design. Ordinary wording that preserves approved semantics may change only in its authoritative implementation file. A proposed change to the invocation contract, router, predicate, terminal, package boundary, reference ownership/load condition, invariant, or authority semantics stops implementation until the design spec is updated and the user aligns with the change; commit the aligned spec before implementation. After any correction, rerun affected matched Sol/Luna RED/GREEN arms only while the approved evidence budget remains, update the complete GREEN ledger without relabeling non-passing evidence, and rerun Task 2's exact-source comparison. Reject contradictory suggestions with quoted spec evidence in the review report.

- [ ] **Step 4: Re-run all static and package validators**

Run:

```bash
uv run plugins/plugin-creator/skills/skill-creator/scripts/quick_validate.py .agents/skills/rebase
uv run prek run skilllint --files .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
uv run prek run markdownlint-cli2 --files .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md
uv run pytest tests/test_validate_codex_skill_activation.py -q
uv run --script scripts/generate_harness_compatibility.py --check
```

Expected: all commands exit zero; generated harness data is current.

- [ ] **Step 5: Re-render Mermaid and recheck package invariants**

Repeat Task 2's Mermaid extraction/render, package listing, no-Python/no-JSON check, exact symlink assertion, process-line count, direct-reference check, and 120/1,024-character audits.

Expected: render succeeds; router is at most 100 process lines; only the approved six package files exist; all budgets and direct routes pass.

- [ ] **Step 6: Check cross-harness discovery and read-only activation**

First run cross-harness discovery and content checks. Read the current harness measurement files for Claude Code, Codex, OpenCode, Hermes, Kimi, and Cursor; confirm each supported discovery root includes either `.agents/skills` or the retained `.claude/skills` symlink. Discover installed harnesses at execution:

```bash
for harness in claude codex opencode hermes kimi cursor-agent; do
  command -v "$harness" 2>/dev/null || true
done
```

While the approved model-call budget remains, use each installed harness's measured non-interactive invocation and a 120-second bounded read-only run. Ask this exact graph question: follow the `Start` path where binding succeeds, the ordinary ancestry-only relation is true, and every result/publication destination already matches; report that terminal node label and the literal reference path on the `Publish` → `Yes` node. Run no Git mutation. Record binary path, version, exact command, exit status, raw response, and the validator-computed package SHA under `$REBASE_EVIDENCE_DIR/cross-harness/`. When the budget is closed, run only discovery and static portability checks and record live consumer behavior as `UNVALIDATED`.

Expected: every permitted live run reports terminal `No change` and path
`references/publication.md`, and names the package SHA later bound as `$FINAL_PACKAGE_SHA`.
Budget-excluded and absent harnesses are recorded as `UNVALIDATED` or unavailable rather than
claimed as live-tested; measured discovery roots and static package compatibility must still pass.

Run the static portability guard:

```bash
test "$(readlink .claude/skills/rebase)" = '../../.agents/skills/rebase'
! rg -n 'Skill\(|CLAUDE_PLUGIN_ROOT|PLUGIN_ROOT|CODEX_HOME|OPENCODE|MCP|hook|/home/|~/' .agents/skills/rebase
```

Expected: both commands exit zero; shared content contains only ordinary Git/prose actions and skill-relative reference paths.

- [ ] **Step 7: Generate activation evidence for the final package SHA**

Run this only after Tasks 4–5 have made every accepted prose correction and both reviewers have approved the resulting content. Compute the canonical package digest with the same function used by the activation validator:

```bash
FINAL_PACKAGE_SHA="$(uv run python - <<'PY'
from pathlib import Path
from scripts.validate_codex_skill_activation import repo_skill_tree_sha256
print(repo_skill_tree_sha256(Path('.agents/skills/rebase')))
PY
)"
printf '%s\n' "$FINAL_PACKAGE_SHA"
```

When the approved model-call budget remains, run the documented real read-only Codex activation
probe and its matrix-generation command against the installed repo-scoped skill. Regenerate, never
hand-edit, `tests/fixtures/rebase-codex-consumer-evidence.json` and
`tests/fixtures/codex-skill-activation-matrix.jsonl`. Require the rebase row to be `PASSED`, resolve
installed `SKILL.md` and `references/publication.md`, contain no `rebase_plan.py`, and report both
`source_tree_sha256` and `installed_tree_sha256` equal to `$FINAL_PACKAGE_SHA`. When the budget is
closed, keep the new task text as a `MAPPED` future probe, clear its unobserved current evidence,
preserve the historical evidence file under its actual SHA/schema, and do not claim it validates the
final package.

Run `uv run --script scripts/generate_harness_compatibility.py --check`; if objective data changed, regenerate it, rerun `--check`, and stage `harness_compatibility.json`. Any later change beneath `.agents/skills/rebase/` invalidates this step and requires fresh subagent reviews, a refreshed GREEN ledger, and final-SHA evidence only when the approved budget permits it.

- [ ] **Step 8: Run the full repository pre-commit suite against the changed files**

Read `docs/linting-and-type-checking.md`, then run `prek` on the exact changed-file list from the merge base rather than unrelated repository files:

```bash
git diff --name-only --diff-filter=ACMR "$(git merge-base HEAD origin/main)" -z | xargs -0 uv run prek run --files
```

Expected: every applicable hook passes. Fix underlying failures and rerun; never use `--no-verify`.

- [ ] **Step 9: Commit valid review corrections and final evidence separately**

If review produced tracked changes, stage only corrected files and commit:

```bash
git add -- .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md scripts/validate_codex_skill_activation.py tests/test_validate_codex_skill_activation.py tests/fixtures/codex-skill-activation-overrides.json tests/fixtures/codex-skill-activation-matrix.jsonl tests/fixtures/rebase-codex-consumer-evidence.json harness_compatibility.json
git diff --cached --check
git commit -m "fix(rebase): address independent review" -- .agents/skills/rebase/SKILL.md .agents/skills/rebase/references/named-stash.md .agents/skills/rebase/references/history-shape.md .agents/skills/rebase/references/conflict-and-ambiguity.md .agents/skills/rebase/references/active-rebase-recovery.md .agents/skills/rebase/references/publication.md scripts/validate_codex_skill_activation.py tests/test_validate_codex_skill_activation.py tests/fixtures/codex-skill-activation-overrides.json tests/fixtures/codex-skill-activation-matrix.jsonl tests/fixtures/rebase-codex-consumer-evidence.json harness_compatibility.json
```

Expected: hooks pass. Generated evidence, when permitted, binds the committed final package SHA;
otherwise the report names stale hashes and final-package consumer behavior as `UNVALIDATED`. If
review changed no implementation, commit only regenerated evidence whose content changed; do not
create an empty commit. End the Task 5 reviewers and report their explicit completion status.

- [ ] **Step 10: Review the exact final HEAD without further writes**

After all Task 5 commits, bind `FINAL_REVIEW_HEAD="$(git rev-parse HEAD)"`. Dispatch fresh Standards and Spec reviewers against that exact commit, the approved spec, complete GREEN ledger, and available activation evidence. Each reviewer records the commit SHA and package SHA and must explicitly pass, using `PASS WITH CONCERNS` when an accepted limitation or `UNVALIDATED` claim remains. A finding returns to Step 3; after correction, update permitted evidence, commit, and repeat both final reviews. No later skill or evidence change may inherit an earlier review.

Expected: both required subagent reviews explicitly record `PASS` or `PASS WITH CONCERNS` for the
same `FINAL_REVIEW_HEAD` and package SHA without changing files. Concerns name every accepted
limitation, `UNVALIDATED` claim, and stale evidence SHA.

---

### Task 6: Publish the Reviewed Branch and Process PR Feedback

**Files:**
- Do not modify product files unless PR feedback demonstrates a defect
- Read: `docs/github-cli-conventions.md`
- Read: the repository `receiving-pr-reviews` skill and its conditional references

**Interfaces:**
- Consumes: reviewed commits, the complete bounded-evidence ledger, and final validation output
- Produces: one pushed branch, one squash-merged PR, addressed reviewer feedback, and verified target-branch terminal state

- [ ] **Step 1: Verify the branch is clean and commits are file-scoped**

Run:

```bash
git status --short --branch
git log --oneline --decorate "$(git merge-base HEAD origin/main)"..HEAD
git diff --check "$(git merge-base HEAD origin/main)"..HEAD
```

Expected: clean worktree and no whitespace errors. The range may contain the already-approved design and implementation-plan commits plus the implementation/test/review commits; it must contain no unrelated work. Do not rewrite or squash local branch history to remove approved design/plan commits.

- [ ] **Step 2: Push all completed commits in one batch**

Read `rules/commit-cadence-and-worktrees.md` and `docs/github-cli-conventions.md`, then push the current named branch once. This is an ordinary new-commit push; do not force-push.

Expected: push exits zero and the remote branch resolves to local `HEAD`.

- [ ] **Step 3: Create one non-draft PR**

Use `/pr` to write a concise body that explains the runtime removal, always-visible Mermaid router, five conditional references, script-free cross-harness activation probe, complete static validation, bounded behavioral evidence, accepted Sol limitation, and five `UNVALIDATED` scenarios. Create the PR against `main`, then verify `draft: false`.

Expected: PR URL exists, head SHA equals local `HEAD`, and the PR is ready for review.

- [ ] **Step 4: Start review monitoring in a background worker**

Load `receiving-pr-reviews`. Start its blocking `--watch` path in a background subagent or background shell task so the interactive coordinator remains available; the watcher returns when new actionable review arrives rather than polling in the foreground.

Expected: watcher is running in background and consumes no repeated foreground check turns.

- [ ] **Step 5: Assess feedback as a whole before editing**

When review arrives, use the receiving-review summary to identify only unresolved actionable comments, questions, approvals, rejections, mergeability/conflicts, and assigned reviewers. Read full bodies only for unresolved items. Group repeated symptoms by shared design cause and compare each proposed change against the approved spec and GREEN evidence before changing files.

- [ ] **Step 6: Address valid review findings and revalidate proportionally**

Apply valid systemic corrections in their authoritative file; rerun affected matched behavioral evidence only while the approved budget remains, then update the GREEN ledger without relabeling unknowns. Always rerun package validators, Mermaid render, focused activation tests, and changed-file hooks. Commit with a file-scoped Conventional Commit and push normally. Reply with evidence; explain technically unsupported requests without making performative edits.

Any accepted skill-package correction loops back through Task 5's independent subagent reviews and final-package activation-evidence generation before the next push. An accepted semantic-contract correction also requires the spec update and user alignment gate. Continue the background watch until unresolved actionable comments and questions are zero.

Expected: no unresolved actionable review comments or questions remain; all required checks pass; PR remains mergeable and ready for review. Force-push still requires separate explicit authority.

- [ ] **Step 7: Bind the reviewed head and recheck authorized merge gates**

The user has already authorized squash-merge after required subagent reviews and checks pass. Immediately before merging, fetch the remote and bind the exact reviewed PR head:

```bash
PR_NUMBER="$(gh pr view --json number --jq .number)"
REVIEWED_HEAD="$(gh pr view "$PR_NUMBER" --json headRefOid --jq .headRefOid)"
git fetch origin
test "$(git rev-parse HEAD)" = "$REVIEWED_HEAD"
test "$(git rev-parse "origin/$(git branch --show-current)")" = "$REVIEWED_HEAD"
test "$(gh pr view "$PR_NUMBER" --json isDraft --jq .isDraft)" = false
test "$(gh pr view "$PR_NUMBER" --json mergeable --jq .mergeable)" = MERGEABLE
gh pr checks "$PR_NUMBER" --required
```

Re-run the review summary after the fetch. Merge authority is usable only when required checks are successful, required subagent reviews explicitly pass or pass with the bounded concerns against the same `$REVIEWED_HEAD`, unresolved actionable feedback is zero, and the PR is non-draft and mergeable. Task 5 evidence hashes must equal that head's package SHA when regeneration was permitted; otherwise the final reviews must name the stale hashes and final-package behavior as `UNVALIDATED`. Any head movement stops the merge and repeats review/validation against the new SHA.

- [ ] **Step 8: Squash-merge and verify terminal PR/base state**

Merge only the bound reviewed head:

```bash
gh pr merge "$PR_NUMBER" --squash --match-head-commit "$REVIEWED_HEAD"
git fetch origin main
gh pr view "$PR_NUMBER" --json state,mergedAt,mergeCommit,baseRefName,headRefOid
MERGE_COMMIT="$(gh pr view "$PR_NUMBER" --json mergeCommit --jq .mergeCommit.oid)"
test "$(gh pr view "$PR_NUMBER" --json state --jq .state)" = MERGED
test "$(gh pr view "$PR_NUMBER" --json baseRefName --jq .baseRefName)" = main
test "$(gh pr view "$PR_NUMBER" --json mergedAt --jq '.mergedAt != null')" = true
test -n "$MERGE_COMMIT"
git merge-base --is-ancestor "$MERGE_COMMIT" origin/main
BASE_OID="$(git rev-parse origin/main)"
```

Expected: merge command exits zero, PR state is `MERGED`, `mergedAt` and squash `mergeCommit.oid` are non-null, base is `main`, recorded `headRefOid` equals `$REVIEWED_HEAD`, and the squash commit is reachable from fetched `origin/main`. Report the PR URL, reviewed head, squash commit, and terminal base OID. Do not force-push.
