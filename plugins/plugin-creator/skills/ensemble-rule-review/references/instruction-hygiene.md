# Instruction Hygiene — Pre-Ship Checklist for Prompts, Skills, and Agents

Run this before shipping any prompt, skill, or agent authored for an ensemble (or its test harness).
It catches the two failure classes that recur when supporting this methodology: leaked implementation
detail, and inconsistent instruction sets across the file set. Each item below is a gate; a file
passes only when every applicable item holds.

## 1. The task prompt is mechanism-agnostic

The shared/task prompt holds only what a real user would type — the task, nothing about how it is
served.

- No output schema, no file paths, no output-location, no "use skill X", no model names in the prompt.
- All reviewer / output / harness mechanism lives in the executor config (the `.claude/` skills and
  agents), never in the prompt.
- Test: could someone who knows nothing about the harness have typed this prompt verbatim? If not,
  it leaks. Move the leaked part into the executor.

In an A/B or multi-arm setup this is load-bearing: detail in the shared prompt does the structuring
work the arms are supposed to do, which conflates the prompt variable with the arm variable and makes
the comparison meaningless.

The same leak appears beyond the prompt. A `SKILL.md`, agent file, or task file that narrates the
system's implementation — its schema, paths, and component names — instead of giving the executing
agent CLEAR, CoVe-checkable instructions for its task is leaking too. §2 holds each executor file to
that standard.

## 2. Audience test every instruction file

Identify each file's RUNTIME reader, then hold it to that standard:

- Executor files — task prompts, worker/agent prompts, execution skills. Reader does one concrete
  task. Keep only: procedure, inputs, output contract, constraints, framed as CLEAR, CoVe-checkable
  instructions for the task — not a description of the system that serves it. Strip rationale, "why",
  architecture explanation, and experimental framing — the executor cannot act on any of it.
- Design / decision files — the pattern skill and its references. Reader decides whether and how to
  apply the pattern. Rationale, theory, and when-to-use ARE the actionable content here; keep them.

The single test for every sentence: is it a command the reader executes, or knowledge it needs to
act? If neither, delete it. Explaining the wiper-fluid system to the driver is noise — e.g. telling
an executing agent where its model is configured, when it cannot change it.

The fix for non-functional prose is deletion, not explanation. Replacing a decorative `(Haiku)` tag
with a paragraph on where the model is set stacks noise on noise — remove the tag and stop.

## 3. Single source of truth — no restated or derived values

A value written in two files will drift. Define it once; reference it everywhere else.

- Model tier: the agent frontmatter `model:` field only. Never restate the tier in skill or prompt
  prose.
- Output schema: one canonical place (the emitter's contract). Reference it from skills and docs;
  do not copy the schema block into multiple files.
- Paths, counts, thresholds: define once. No derived counts in prose (e.g. "5 workers" computed from
  the group count) — state the source, not the derived number.

## 4. Consistency across the file set

- In a multi-arm setup, the arms must differ ONLY in the variable under test. Diff the arm pair: any
  divergence that is not the independent variable is a bug.
- The executor's declared inputs and outputs must match what the orchestrator or runner actually
  passes — e.g. an agent that says "the single file under review" while the arm passes a file list is
  inconsistent.
- Schema field names, ordering tolerance, and field semantics are identical across every file that
  emits or parses them (the corroboration key especially — `group` and the `location` format).

## 5. Review the harness artifacts with the methodology itself

The prompts, skills, and agents are AI-facing prompt-engineering code, subject to the same review as
any other input. Before shipping, run them through a review pass — ideally fresh-eyes (a separate
agent), because the author is blind to their own decoration and leaks. Apply items 1-4 as the rubric.

## 6. Self-application — review created skills with this methodology

Items 1-4 above (plus the conversion-workflow fidelity audit) are themselves a ruleset of 10+ criteria
applied to instruction files, so reviewing a skill's rules is itself an ensemble-rule-review candidate.
When a skill creates or converts another skill, review the new skill's instructions with a MIXED fleet,
each check routed by its error structure (the candidate-fit fit-killer applied to this checklist):

- Mechanical / greppable checks — restated model tier in prose, schema duplicated across files, derived
  counts, leaked schema/paths in the task prompt, location-format mismatch. Fan these out across
  overlapping cheap `focused-reviewer` workers, corroborate on (check, location), drop the tail.
  Independent attention lapses cancel; this is the bounded half and the cheapest first pass.
- Judgment checks — does this prose present a parameter as the design vs a default? is this rationale
  actionable for the file's audience? has a reframe over-corrected into the opposite bias? Route these to
  a heterogeneous capable panel (different model families / lenses), reduce by synthesis, and put an
  independent different-model verifier on the survivors. A homogeneous cheap panel would share the
  misjudgment and corroboration would amplify it.

Run the cheap mechanical pass first; escalate only the judgment checks. This is the methodology reviewing
its own output — the same Detect -> (Design) -> Verify shape, with tier and diversity set per check, not
fixed. See [./candidate-fit.md](./candidate-fit.md) for the mechanical-vs-judgment split and the parent
SKILL.md Composition Framework for the fleet knobs.

## 7. Correcting a rule — state it as a knob, and defend the default

When a review finds a parameter stated as a fixed value (a model tier, a worker count, "cheap",
"homogeneous"), the fix is to restate it as a knob with a "match to X" criterion — not to swap one
absolute for another. The origin example's setting is one point on the knob, not the axis.

When the correction reframes an over-narrow default, run an adversarial defender of that default
before shipping the reframe: a reviewer whose only job is to argue the original setting is sometimes
right. This prevents the reframe over-correcting into the opposite bias — "always cheap/homogeneous"
becoming "always capable/heterogeneous". The de-bias of this skill used exactly this step: an
adversarial-defender pass kept the cheap-mechanical path as a real option instead of deleting it.

SOURCE: observed failures while building the SOLID A/B harness for this methodology
(session 2026-06-03). A shared task prompt carried the output schema, ruleset/corpus/findings paths,
the location format, and a "follow skill X" instruction. Executor files carried decorative `(Haiku)`
and "high-intelligence pass" annotations and an explanation of where the model is configured. The
output schema was duplicated across the README, the arm skills, and the arm agents, with drifted
field order and `rule` semantics. An arm agent declared a "single file" input while the arm reviewed
the whole corpus. Each was a prompt-engineering bug — incorrect agent behavior from imprecise prose,
the same way a logic error produces incorrect program behavior.
