# Working in dh Workflow Files

A process for making changes to the groom, work, and plan workflows in the development-harness plugin. This document captures the methodology required to assess, implement, and verify changes that touch the multi-stage pipeline.

---

## Why this process exists

The dh workflows are a pipeline. Each stage file (`intake.md`, `analyze.md`, `swarm.md`, `finalize.md`) has a defined contract: it receives specific data from the prior stage and produces specific data for the next. A change that looks local to one file almost always has upstream and downstream effects — data that must be derived differently, output that must be consumed, validation gates that must be updated, or execution paths that diverge from what was described.

The wave-0 research change (adding `technical-researcher` to the groom swarm) required touching `swarm.md`, `finalize.md`, and the Wave 0 sequence diagram. At the time, `swarm.md` still described two dispatch paths (a team-mode and a no-team fallback, later consolidated into the single wave sequence described above), and both needed updating in step. It required knowing that the Research section must be excluded from the required-sections validation gate because Wave 0 is skippable. None of this was visible from reading only the file being changed.

This process makes that chain of reasoning explicit.

---

## Before You Touch Any File

### Step 1 — Name the change precisely

Write one sentence stating:
- What is being added, removed, or modified
- Which stage of the pipeline it lives in
- What it produces

Example: *"Adding a pre-swarm research step (Wave 0) to `swarm.md` that runs `technical-researcher` before Wave 1 and writes a Research section to the backlog item."*

If you cannot write this sentence, you do not have enough clarity to make the change.

### Step 2 — Read the prior stage file

Do not rely on memory. Use agents to read the actual file. Extract:

- What data it outputs to your stage (field names, formats, conditions)
- What terminal states it can produce (SKIP, STOP, BLOCKED, PROCEED)
- What it passes to the swarm or next step

**The prior stage controls what your change can receive.** If your change needs data that the prior stage does not produce, the prior stage must be updated too.

For the groom pipeline, the chain is: `intake.md` → `analyze.md` → `swarm.md` → `finalize.md`

### Step 3 — Read the downstream stage file

Extract:
- What sections or artifacts it expects to exist after your stage
- What it validates (required sections, minimum content, format checks)
- What it passes to the next stage after that
- What terminal states it can produce

**Your change's output becomes the downstream stage's input.** If your change adds a new section or artifact, the downstream stage must know about it.

### Step 4 — Read finalize.md regardless of where your change is

`finalize.md` is the validation gate for the entire swarm. It defines:
- Which sections are required (validated for presence and minimum content)
- Which sections are optional (explicitly listed — absence is not an error)
- The retry logic when sections are missing
- The RT-ICA Final Pass — which sections are read to re-assess conditions
- The groomer input list — what data the groomer receives

If your change adds a new section, it must appear in one of these categories in `finalize.md`. An omission means the section is neither validated nor explicitly excluded — the pipeline has no defined behavior for it.

---

## Mapping the Data Contract

For every change, document these four things:

| | Question | Where to find the answer |
|---|---|---|
| **Input** | What exact fields does my change receive? From which prior stage? | Read the prior stage's Outputs section |
| **Derivation** | If my change needs data that isn't passed directly, how is it derived? | Read the item's structure, RT-ICA conditions, scope sizing output |
| **Output** | What does my change write? To which section? In what format? | Define this before touching any file |
| **Failure** | If my change fails (BLOCKED, error, no findings), what does the downstream stage do? | Read the downstream stage's handling for missing sections |

The wave-0 change required resolving all four:
- **Input**: item description, RT-ICA DERIVABLE/MISSING conditions, scope sizing decision, item_ref — all from `analyze.md` outputs
- **Derivation**: `technology` and `concern` must be derived from the item description and RT-ICA conditions (not passed as named fields)
- **Output**: Research section written to backlog item via `backlog_groom`
- **Failure**: if BLOCKED, Wave 1 proceeds without research prior context — finalize.md must not require Research and must not block the groom on its absence

---

## Checking the Dispatch Sequence

The groom swarm runs as three dependency-ordered waves, each dispatched as plain `Agent()` calls
(no team) with a Mermaid sequence diagram per wave in `swarm.md`. The sequence diagram is the
primary reference — if it is stale, agents following it will produce wrong output.

Checklist when modifying swarm.md:
- [ ] Updated the wave sequence diagram(s) affected by the change
- [ ] Verified the `## Dependencies` table if agent dependencies changed
- [ ] Updated the `## Agents` list if a new agent role was added

---

## Checking Skip Conditions

Every addition to a pipeline stage needs an explicit answer to: **when does this NOT run?**

Skip conditions matter because:
- Downstream stages must not require output from a skipped step
- The validation gate (finalize.md) must categorize the output as optional, not required
- The sequence diagram must show the skip branch

For Wave 0: skip when item type is `type:bug` or `type:fix`, when no technology is identifiable, or when the item is administrative. This skip decision is not in `finalize.md` — it lives in `swarm.md` — but `finalize.md` must reflect it by excluding Research from required sections.

---

## Updating finalize.md

`finalize.md` is the authoritative record of what a completed groom looks like. When your change produces new output:

1. **Required output** (groom fails without it): add to the required sections table with minimum content definition
2. **Optional output from a skippable step**: add to the optional sections list with a note explaining when it is absent and that absence does not block the groom
3. **Prior context read by the RT-ICA Final Pass**: add to the "Extract:" line at the start of the RT-ICA Final Pass section
4. **Input to the groomer**: add to the groomer input list in swarm.md's Groomer prompt section

The wave-0 change required all four: Research section added to optional list (with skip note), added to Extract list, added to groomer input list, and the Wave 0 sequence diagram updated.

---

## Verifying the Change End-to-End

Before committing any workflow change:

1. **Trace the happy path**: walk through intake → analyze → swarm (with your change) → finalize for a representative item. Confirm data flows correctly at each stage boundary.

2. **Trace the failure path**: walk through what happens when your change returns BLOCKED or produces no output. Confirm downstream stages handle this gracefully.

3. **Trace the skip path**: walk through what happens when your change is skipped entirely (bug/fix item, or whatever the skip condition is). Confirm the groom still completes.

4. **Check the wave sequence diagrams**: verify every wave's Mermaid diagram in swarm.md reflects the change.

5. **Write evals**: define structured test cases using the actual invocation format (the args the upstream caller passes), not user-facing research questions. Run with-skill vs without-skill to confirm the change adds value.

---

## When a Change Touches the Skill Layer (Angle Skills, Synthesis Skills)

If your change involves skills invoked from within the pipeline:

1. **Verify the invocation chain**: who invokes the skill? (The agent that loads the skill via `Skill()`, not the orchestrator that spawned that agent.) What args does the invoker pass? The args become `$ARGUMENTS` in the skill body.

2. **Check tool availability**: what tools does the invoking agent have? Skills inherit the invoking agent's tool list. A skill whose workflow calls `Grep` will silently fail if the agent does not have `Grep` in its `tools:` frontmatter.

3. **Use the optimizer**: after writing a skill, delegate to `plugin-creator:ai-doc-optimizer` before writing evals. The optimizer catches: missing tool routing in procedural steps, missing STATUS output blocks, redundant constraints, positive-framing violations, and mismatches between the output template and the workflow steps that produce it.

4. **Write evals with actual args**: the eval prompt for an angle skill is the args string the orchestrator would pass, not a user-facing research question.

---

## Reference: groom pipeline stage files

| File | Stage | Primary output |
|---|---|---|
| `intake.md` | Validate and extract item | Item fields: title, description, priority, labels, groomed, research_first, suggested_location |
| `analyze.md` | Discovery gate, RT-ICA baseline, scope sizing | Feature-context artifact, RT-ICA snapshot, scope sizing decision (MINIMAL/NARROW/STANDARD/FULL) |
| `swarm.md` | Parallel grooming agents + Wave 0 research | Research section (Wave 0), Impact Radius, Fact-Check, RT-ICA, Issue Classification, groomed subsections |
| `finalize.md` | RT-ICA final pass, validation gate, write | Groomed item with `mark_groomed=True`, terminal state |

Source: groom workflow files under `skills/work-backlog-item/references/workflows/groom/`
