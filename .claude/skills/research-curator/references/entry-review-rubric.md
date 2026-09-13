# Research Entry Review Rubric

How to review a finished research entry and the analysis files produced from it.

Writing an entry rather than reviewing one? Use [Entry Quality Standards](./entry-quality-standards.md) and [Extraction Methodology](./extraction-methodology.md) instead — this rubric is the audit that runs afterwards.

**Review scope** — every file the entry's creation touched:

- The entry: `./research/{category}/{name}.md`
- Improvement proposals, when present: `./research/insights/{YYYY-MM-DD}-{name}-improvements.md`
- Utilization proposals, when present: `./research/insights/{YYYY-MM-DD}-{name}-utilization.md`
- Cited entries, when the entry added cross-references to them

**Completion criterion**: every gate below has been run and its result recorded. A gate you skipped is a gate that FAILED — record it as `NOT RUN` with the reason, never as a pass.

**Defect** = any finding under any gate. Record every defect as `{file}:{line} — {gate} — {exact quoted text} — {required correction}`. Quote the offending text verbatim; paraphrase loses the reviewer's evidence.

---

## Gate 1 — Mechanical Checks

Run all three commands. Report their output as **exact counts per severity and the verbatim issue lines** — "mostly clean", "a few warnings", and "passes validation" are not review output.

```bash
uv run --script .claude/skills/research-curator/scripts/fix_research_formatting.py --check ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py main --json ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py check-backlinks ./research
```

| Command | What a defect looks like | Record |
|---|---|---|
| `fix_research_formatting.py --check` | Non-zero exit — the file needs formatting fixes | Every path the tool named, and the fix it wanted. `--check` does not write; drop `--check` only when this review is also applying fixes |
| `validate_research.py main --json` | Any issue in the JSON `entries[].issues[]` array | `errors: N, warnings: N, info: N` from `summary`, then every issue's `check`, `severity`, `message`, and `line`, quoted |
| `validate_research.py check-backlinks ./research` | Any asymmetric cross-reference involving this entry | Each asymmetric pair by both paths. Run without `--fix` to review; `--fix` repairs but hides what was wrong |

**Cross-reference reciprocity** is measured by `check-backlinks`, not by eye. An entry that cites B while B does not cite back is a defect against this entry even though the missing row lives in B. Row format: [Cross-Reference Format](./cross-reference-format.md).

---

## Gate 2 — Fidelity Rules

Each rule in [Entry Quality Standards](./entry-quality-standards.md) is a separate check with its own verdict. Run all five; one rule's pass says nothing about another's.

| Check | Question | Defect |
|---|---|---|
| **Rule 1 — Read Before Writing** | Does every section's content trace to a source listed in References, and was that source actually reachable? | A claim whose only possible basis is the resource's name, URL path, or domain. An inaccessible source whose absence is not stated in References |
| **Rule 2 — Preserve Counts** | Are capability figures written as the exact number the source gives? | A vague quantifier ("many languages", "recent release", "low latency") standing where the source has a figure |
| **Rule 2a — No Popularity Statistics** | Is the entry free of star, download, fork, and contributor counts? | Any such figure anywhere in the entry, including inside a badge, a quoted README passage, or a "Key Statistics" section that should not exist |
| **Rule 3 — Absence vs Nonexistence** | Where information was not found, does the entry say it was not found? | "Doesn't support X" / "Not available" / "Not supported" where the honest statement is "Not mentioned in documentation" or "Unable to access {source}" |
| **Rule 4 — Explicit Confidence** | Does every major section carry a confidence level in the confidence map? | A section missing from the map. A `high` on a section whose sources are informal, partial, contradictory, or code-read |

---

## Gate 3 — Depth

Score each section against its bar in [Entry Quality Standards](./entry-quality-standards.md#depth-requirements). Present-but-thin is a defect; the section existing is not the bar.

| Section | Passes when | Defect |
|---|---|---|
| **Technical Architecture** | Names components with their exact source names, describes data flow or execution model, and names extension or integration points | "Uses a plugin-based architecture" with no component named and no mechanism given |
| **Key Features** | Each feature states what it does AND the mechanism by which it does it | A feature list that is a list of outcomes with no mechanism |
| **Installation & Usage** | At least one complete example taken verbatim or near-verbatim from official docs; install command verified against official docs | An install command assembled from a guessed package name. A usage example with no source behind it |
| **Limitations and Caveats** | Present, with either documented limitations or the explicit low-confidence absence statement | Section missing, empty, or filled with "N/A" |

---

## Gate 4 — Repo Claims Verified Against the Repo

Every statement an entry or an analysis file makes about **this repository** is a claim to verify against the actual files, not a claim to accept. This gate covers the entry's "Relevance to Claude Code Development" section and every proposal in the `-improvements.md` and `-utilization.md` files.

For each repo claim, in order:

1. **Path exists** — read the path the claim names. A proposal resting on a path that is not in the repo is a defect, full stop. Resolve it yourself; do not assume a near-miss was a typo.
2. **Path is described correctly** — the file's real contents match what the claim says about them. A proposal that names a real path but misdescribes what lives there is a defect of the same severity as an invented path.
3. **Gap is real** — where a proposal says the local system lacks a capability, the file confirms the absence. A capability the file already implements makes the proposal a defect, not a low-confidence proposal.
4. **Measurable signal is runnable** — where a proposal names a command or an observable field as its completion signal, that command runs and that field is reachable.

Record each verified claim with the path you read. A gate 4 pass asserts you opened the files; it cannot be reached by reading the proposal alone.

---

## Gate 5 — Did the Analysis Engage This Repo?

Judgment check, applied to the entry's "Relevance to Claude Code Development" section and to both analysis files.

Ask: **could this text have been written about any Python repository without opening this one?**

- **Passes** when the analysis names specific files, skills, agents, or workflows of this repo and says something about them that is true here and would be false elsewhere.
- **FAILS** when the analysis would survive a find-and-replace of this repo's name — generic advice ("could improve code quality", "useful for agent workflows", "fits well with this project's architecture") dressed as repo-specific findings.

A gate 5 failure is a defect even when every individual sentence in gate 4 verified: correct-but-generic analysis is the failure mode this gate exists to catch.

---

## Gate 6 — Hallucination Triggers

Scan the entry and both analysis files for each trigger. Quote every hit.

| Trigger | Scan for | Defect unless | Required correction |
|---|---|---|---|
| **Speculation language** | "I think", "likely", "probably", "seems", "should be", "assume", "maybe", "might" | The phrase sits inside a verbatim quotation from a primary source, attributed as such | Replace with what the source states, with "Not mentioned in documentation" per Rule 3, or with the steps taken and what was observed |
| **Causality without evidence** | "because", "due to", "caused by", "therefore", "this means", "as a result" | The sentence cites the specific observation behind it — a source passage, a file and line, a command's output | Rewrite as an observation alone, or as an explicit hypothesis plus the verification step that would settle it |
| **Pseudo-quantification** | Scores and percentages — "8.5/10", "70% faster", "100% coverage" | The figure is quoted from a primary source with its method, or the entry states the method used to produce it | Replace with the measured evidence, or remove the figure |
| **Completeness overclaims** | "all files checked", "comprehensive analysis", "fully resolved", "everything fixed", "every skill reviewed" | The text lists the concrete checks performed and their scope | List what was inspected and with what scope, or narrow the claim to what was actually covered |

SOURCE: Triggers 1–4 adapted for research-entry content from the `hallucination-detector` plugin's `commands/hallucination-audit.md` (<https://github.com/bitflight-devops/hallucination-detector>, accessed 2026-09-13); also reachable in this repo as the `/hallucination-detector:hallucination-audit` command.

---

## Verdict

Report in this form:

```text
REVIEW: ./research/{category}/{name}.md

GATE 1 mechanical:    PASS | FAIL | NOT RUN ({reason})
  fix_research_formatting --check: exit {N}
  validate_research main --json:   errors {N}, warnings {N}, info {N}
  check-backlinks:                 {N} asymmetric pairs
GATE 2 fidelity:      PASS | FAIL — rules failed: {1|2|2a|3|4}
GATE 3 depth:         PASS | FAIL — sections failed: {names}
GATE 4 repo claims:   PASS | FAIL — {N} claims verified, {N} defective
GATE 5 engagement:    PASS | FAIL
GATE 6 triggers:      PASS | FAIL — triggers hit: {names}

DEFECTS: {N}
1. {file}:{line} — GATE {N} — "{exact quoted text}" — {required correction}
2. ...

VERDICT: APPROVE | REQUEST CHANGES
```

`APPROVE` requires every gate at PASS and `DEFECTS: 0`. Any gate at FAIL or NOT RUN, or any defect recorded, is `REQUEST CHANGES` — a defect count above zero and an `APPROVE` verdict cannot both be true.
