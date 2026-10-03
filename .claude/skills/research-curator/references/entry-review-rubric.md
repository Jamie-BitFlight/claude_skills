# Research Entry Review Rubric

How to review a finished research entry and which findings the reviewer fixes itself.

Writing an entry rather than reviewing one? Use [Entry Quality Standards](./entry-quality-standards.md) and [Extraction Methodology](./extraction-methodology.md) instead — this rubric is the audit that runs afterwards.

**Review scope** — every file the entry's creation touched:

- The entry: `./research/{category}/{name}.md`
- Cited entries, when the entry added cross-references to them

The rubric reviews the entry itself ([scope](./entry-quality-standards.md#scope)). Gates 2-4 skip a pre-existing `## Relevance to Claude Code Development` section and any popularity-statistics block (`Key Statistics`): neither is scanned, mapped or counted, and the worker leaves both as found.

**Completion criterion**: every gate below has been run and its result recorded. A gate you skipped is a gate that FAILED — record it as `NOT RUN` with the reason, never as a pass.

**Defect** = a finding in the entry or a file the reviewer may write. Record every defect as `{file}:{line} — {gate} — {exact quoted text} — {required correction}`. Quote the offending text verbatim; paraphrase loses the reviewer's evidence.

**Repair** = a finding in a file the reviewer may not write, such as a missing backlink row in an `--exclude`d file. The orchestrator appends each `R` line from the repair result; the reviewer does not write or act on it. Format: `{file}:{line} — {gate} — {exact quoted text} — {required correction}`. Repairs are counted apart from defects and leave the verdict where it stood.

---

## Gate 1 — Mechanical Checks

Run the formatter. The orchestrator runs the validator after every pass, appending its remaining issues to the scratch document as `D` lines, and repairs cross-reference reciprocity before review; an orchestrated review (it names a scratch document) skips those two commands, and a standalone `--review` runs all three. Report output as **exact counts per severity and the verbatim issue lines** — "mostly clean", "a few warnings", and "passes validation" are not review output.

```bash
uv run --script .claude/skills/research-curator/scripts/fix_research_formatting.py --check ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py main --json ./research/{category}/{name}.md
uv run --script .claude/skills/research-curator/scripts/validate_research.py check-backlinks ./research
```

| Command | What a defect looks like | Record |
|---|---|---|
| `fix_research_formatting.py --check` | Non-zero exit — the file needs formatting fixes | Every path the tool named, and the fix it wanted. Run it without `--check`: this review applies fixes, so a path it reformatted is a checked finding |
| `validate_research.py main --json` | Any issue in the JSON `entries[].issues[]` array except `cross_references_absent`, non-blocking per [Validation Rules](./validation-rules.md) | Counts of blocking issues only (`cross_references_absent` excluded, so they can differ from `summary`): `errors: N, warnings: N`, then every blocking issue's `check`, `severity`, `message`, and `line`, quoted |
| `validate_research.py check-backlinks ./research` | A residual asymmetric cross-reference involving this entry, or any file the scan could not read or parse | Each object in JSON `edges`, and every object in `skips` when `scan_skipped_files` is non-zero. `--fix` retains the original `edges` and adds repair outcome fields |

A non-zero `scan_skipped_files` field fails this command on its own, because a file dropped from
the scan was never compared -- exit 0 would claim coverage the scan did not have. Treat those
paths as Gate 1 defects, not as noise.

**Cross-reference reciprocity** is measured by `check-backlinks`, not by eye, and repaired by the orchestrator; the reviewer reports only a residual pair. An entry that cites B while B does not cite back is a defect against this entry even though the missing row lives in B. Row format: [Cross-Reference Format](./cross-reference-format.md). A pair whose missing row is in an `--exclude`d or unwritable file is an `R` line, not a `D` line; the final verdict block relays `R` lines to the user, and no worker acts on them.

---

## Gate 2 — Fidelity Rules

Each rule in [Entry Quality Standards](./entry-quality-standards.md) is a separate check with its own verdict. Run every rule below; one rule's pass says nothing about another's.

| Check | Question | Defect |
|---|---|---|
| **Rule 1 — Read Before Writing** | Does every section's content trace to a source listed in References, and was that source actually reachable? | A claim whose only possible basis is the resource's name, URL path, or domain. An inaccessible source whose absence is not stated in References |
| **Rule 2 — Preserve Counts** | Are capability figures written as the exact number the source gives, and every snapshot (version, figure, status) written with the date it was read? | A vague quantifier ("many languages", "recent release", "low latency") standing where the source has a figure. A snapshot written without its date |
| **Rule 3 — Absence vs Nonexistence** | Where information was not found, does the entry say it was not found? | "Doesn't support X" / "Not available" / "Not supported" where the honest statement is "Not mentioned in documentation" or "Unable to access {source}". |
| **Rule 4 — Explicit Confidence** | Does every major section carry a confidence level in the confidence map? | A section missing from the map. A `high` on a section whose sources are informal, partial, contradictory, or code-read |
| **Scope** | Is the entry a summary of the researched resource only? | A claim about this repository, or a Relevance section, in a new entry |

---

## Gate 3 — Depth

Score each section against its bar in [Entry Quality Standards](./entry-quality-standards.md#depth-requirements). Present-but-thin is a defect; the section existing is not the bar.

| Section | Passes when | Defect |
|---|---|---|
| **Technical Architecture** | Names components with their exact source names, describes data flow or execution model, names extension or integration points, and gives the documented design rationale or the Rule 3 absence statement | "Uses a plugin-based architecture" with no component named and no mechanism given |
| **Key Features** | Each feature states what it does AND the mechanism by which it does it | A feature list that is a list of outcomes with no mechanism |
| **Installation & Usage** | At least one complete example taken verbatim or near-verbatim from official docs; install command verified against official docs | An install command assembled from a guessed package name. A usage example with no source behind it |
| **Limitations and Caveats** | Present, with either documented limitations or the explicit low-confidence absence statement | Section missing, empty, or filled with "N/A" |

---

## Gate 4 — Hallucination Triggers

Scan the entry for each trigger. Quote every hit.

| Trigger | Scan for | Defect unless | Required correction |
|---|---|---|---|
| **Speculation language** | "I think", "likely", "probably", "seems", "should be", "assume", "maybe", "might" | The phrase sits inside a verbatim quotation from a primary source, attributed as such | Replace with what the source states, with "Not mentioned in documentation" per Rule 3, or with the steps taken and what was observed |
| **Causality without evidence** | "because", "due to", "caused by", "therefore", "this means", "as a result" | The sentence cites the specific observation behind it — a source passage, a file and line, a command's output | Rewrite as an observation alone, or as an explicit hypothesis plus the verification step that would settle it |
| **Pseudo-quantification** | Scores and percentages — "8.5/10", "70% faster", "100% coverage" | The figure is quoted from a primary source with its method, or the entry states the method used to produce it | Replace with the measured evidence, or remove the figure |
| **Completeness overclaims** | "all files checked", "comprehensive analysis", "fully resolved", "everything fixed", "every skill reviewed" | The text lists the concrete checks performed and their scope | List what was inspected and with what scope, or narrow the claim to what was actually covered |

These four triggers are copied in **by decision, not by fallback, and scoped to Gate 4 only** —
this does not contradict `AGENTS.md`'s skill-policy table routing "Reviewing agent output" to
`/hallucination-detector:hallucination-audit` for other review contexts. Nothing under
`.claude/skills/research-curator/`, or in the agents it spawns, calls that plugin; the plugin is not
in `enabledPlugins` in `.claude/settings.json`, so `/hallucination-detector:hallucination-audit` is
not reachable in this checkout; and, after following the generation prerequisite in `AGENTS.md`, the
generated `harness_compatibility.json` view carries no entry for it, so it is reachable in no other
harness either. Whether it is enabled is therefore not a question this gate's
behaviour turns on. Do not re-open it, and do not replace this table with a call to that plugin or
any other out-of-skill route: everything Gate 4 needs lives under
`.claude/skills/research-curator/`.

SOURCE: Triggers 1–4 adapted for research-entry content from the `hallucination-detector` plugin's `commands/hallucination-audit.md` (<https://github.com/bitflight-devops/hallucination-detector>, accessed 2026-09-13) — copied in and re-scoped, not referenced. Plugin availability read from `.claude-plugin/marketplace.json`, `.claude/settings.json` `enabledPlugins`, and the generated `harness_compatibility.json` view (2026-09-13); follow the `AGENTS.md` generation prerequisite before reading that view. `AGENTS.md` Repository Overview states the plugin is "not enabled by default in every install".

---

## Findings Document

One per entry, at the path the invocation names, kept across rounds; the reviewer and the `--fix` worker both write it. The reviewer writes every defect and repair as an unchecked line before fixing any. Whoever acts on a line adds `did:` with a short action note, and checks the line off once its fix is re-found in the file.

```text
- [ ] D1 | gate {N} | {file}:{line} | "{exact quoted text}" | {required correction}
- [x] D2 | gate {N} | {file}:{line} | "{exact quoted text}" | {required correction} | did: {what changed}
- [ ] D3 | gate {N} | {file}:{line} | "{exact quoted text}" | needs: {data to gather, and from where} | did: {what was tried}
```

`D` marks a defect, `R` a repair; ids stay fixed across rounds. The reviewer edits no tracked file except the entry; this document and temp files are unrestricted.

**Loop**: a sonnet reviewer and a haiku worker share this document. The orchestrator runs at most 5 review rounds and stops early when a round's unchecked `D` ids equal the previous round's (`R` lines are excluded from the comparison). After either stop, a `FAIL` with an unchecked line in gate 1 or 4 (mechanical) or a `NOT RUN` gate is reported `UNRESOLVED`, a process defect of the instructions, not of the entry. A `FAIL` with unchecked lines in gates 2 and 3 only (semantic) is `ACCEPTED` as best effort, and the source is the truth.

**Fix with no additional research:** reword; restructure; add a missing section from material already in the entry or in files already cited or opened; fix a quote re-found in a file already available; remove a claim that cannot be sourced. Re-running a recorded command to check it is verification, not research.

**Leave unchecked** any correction that needs data gathering to validate — fetching upstream sources — with `needs:` stating the data. A finding in a file outside the writable set is an `R` line, not a `D` line.

**Rounds after the first** (the invocation says which): review the worker's changes and research, not only the lines. Run every gate over the files again and check each `did:` note against the file and the source it cites; a checked line whose fix is absent or wrong reopens unchecked. Add a line only for a defect a gate defines; prose no gate names is not a finding. A closed finding set is what lets rounds converge. A gate whose findings recur across rounds marks creator and reviewer instructions that disagree; the orchestrator reports its id.

---

## Verdict

Report in this form. Gate lines record the state after this pass's fixes; the defects themselves live in the findings document.

```text
REVIEW: ./research/{category}/{name}.md
SCRATCH: {findings document path}

GATE 1 mechanical:    PASS | FAIL | NOT RUN ({reason})
  fix_research_formatting:         exit {N}
  validate_research main --json:   orchestrator | errors {N}, warnings {N}
  check-backlinks:                 orchestrator | {N} asymmetric pairs, {N} scan-skipped files
GATE 2 fidelity:      PASS | FAIL — rules failed: {1|2|3|4|Scope}
GATE 3 depth:         PASS | FAIL — sections failed: {names}
GATE 4 triggers:      PASS | FAIL — triggers hit: {names}

DEFECTS: {N} found, {N} checked, {N} unchecked
REPAIRS: {N} found, {N} checked, {N} unchecked

UNCHECKED: (each unchecked line, verbatim)
- [ ] D3 | gate {N} | ...

VERDICT: PASS | FAIL | FAIL -- NOT RUN: {reason}
```

`PASS` requires every gate at PASS and no unchecked defect. Any gate at FAIL or NOT RUN, or any unchecked defect, is `FAIL` — an unchecked defect and a `PASS` verdict cannot both be true. A `NOT RUN` gate gives `FAIL -- NOT RUN: {reason}` with no line for the worker; the orchestrator stops on it, naming the gate.

An `R` line is set aside: an entry whose only unchecked lines are `R` lines is `PASS` and keeps its README row. A gate whose only findings are `R` lines is `PASS`.
