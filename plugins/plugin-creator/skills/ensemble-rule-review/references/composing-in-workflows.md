# Composing the Pattern Inside Multi-Phase Workflows

A sequential or multi-phase workflow is NOT disqualified from this pattern. The whole pipeline
is not the unit of conversion — each PHASE is. Keep the sequential outer control flow; convert
each phase that does rule-following or independent parallel work into its own fan-out agent set.
The workflow is the conductor; each phase is its own fan-out.

Do NOT score a multi-phase skill against the "When to Use" gate as one unit. Score EACH phase.

## Two flavors of fan-out

| Flavor | Input | Corroboration | Use for |
|--------|-------|---------------|---------|
| **Ensemble-denoising** (this skill's core) | SAME input to every worker; overlapping rule slices | yes — weighting denoises cheap workers | rule-following / review / rubric phases |
| **Work-partition** | disjoint, independent work items | no — pure speedup | generative / independent-work phases |

A phase picks its flavor by what it does:

- **Checking against a ruleset** → ensemble-denoising (overlap + corroboration).
- **Producing independent artifacts** → work-partition (parallelize the items).
- **One coherent creative judgment** → neither; keep a single agent (partitioning loses the
  whole-picture context the judgment needs).

## Worked map: stinkysnake's 9 phases

SOURCE: `plugins/python-engineering/skills/stinkysnake/SKILL.md` (verified 2026-05-30).

| Phase | What it does | Fan-out flavor |
|-------|--------------|----------------|
| 1 Static analysis | runs ruff/ty (deterministic tools) | a script, not an agent fan-out; manual-issue triage is a mild ensemble |
| 2 Type analysis | inventory `Any`, map type deps, find gaps | ensemble-denoising — one worker per gap-criterion, overlapping |
| 3 Modernization planning | per-`Any` construct selection + PEP/library roster | ensemble-denoising — one worker per construct/PEP scanning for opportunities (strongest) |
| 4 Plan review | review plan vs pythonic / feasibility / breaking changes | ensemble-denoising — multi-dimension review (this is code-review) |
| 5 Refinement | edit the plan per review feedback | neither — sequential edit |
| 6 Docs discovery | find docs needing update | work-partition — each doc independent |
| 7 Interface design | design protocols/types | neither — coherent creative judgment |
| 8 Test-first | write failing tests per interface | work-partition — parallel by interface |
| 9 Implementation | implement functions in dependency order | work-partition — independent functions, bounded by dependency order |

The conversion targets inside this workflow are the rule-bearing phases (2, 3, 4), each becoming
an internal ensemble; the producing phases (6, 8, 9) become work-partition fan-outs; the outer
phase ordering stays sequential.

## Conversion rule for multi-phase skills

1. List the phases.
2. Classify each: rule-following (ensemble), independent-work (work-partition), or
   creative-coherence (single agent).
3. Convert each ensemble phase per [./conversion-workflow.md](./conversion-workflow.md) and each
   independent-work phase as a parallel work split.
4. Preserve the sequential ordering and the artifact each phase passes to the next.
5. Validate per-phase against its single-pass baseline, not the pipeline as a whole.
