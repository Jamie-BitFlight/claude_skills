# Research Entry Review Rubric

How to decide whether a finished research entry is worth having.

Writing an entry rather than reviewing one? Use [Entry Quality Standards](./entry-quality-standards.md)
and [Extraction Methodology](./extraction-methodology.md). This rubric is the audit that runs
afterwards, and it deliberately does not score everything those files ask a writer to do.

An entry has two jobs:

1. **Deliver a reader to the canonical source, dated.** An agent that needs a fact about the subject
   reads the source, not this summary. The entry is the pointer and the reason to follow it — never
   the authority on the subject.
2. **Say what this repository should do about the subject, in terms that are true here.** Nothing
   but this repo's own files can settle such a claim, and a wrong one costs a reader a wasted
   session.

Those two jobs are the two gates. **Only the checks below produce defects.** Depth, prose quality,
per-section confidence levels, exact capability figures, markdown formatting, and cross-reference
symmetry are not reviewed here: the writing standards govern the first four, `prek` (Post-Actions
step 4) governs formatting, and `check-backlinks --fix` (Post-Actions step 2) repairs cross-reference
symmetry deterministically before any review runs. Re-adjudicating them by hand changes nothing
about the entry and buries the two findings that do.

**Review scope**:

- The entry: `./research/{category}/{name}.md`
- Improvement proposals, when the invocation names one: `./research/insights/{YYYY-MM-DD}-{name}-improvements.md`
- Utilization proposals, when the invocation names one: `./research/insights/{YYYY-MM-DD}-{name}-utilization.md`

**Completion criterion**: both gates have been run and their results recorded. A gate you skipped is
recorded `NOT RUN` with the reason — never as a pass.

**Defect** = any finding under either gate. Record every defect as
`{file}:{line} — GATE {1|2} — {exact quoted text} — {required correction}`. Quote verbatim;
paraphrase loses the evidence.

---

## Gate 1 — Can a reader reach the canonical source?

This gate decides the verdict. An entry that cannot deliver a reader to the source, or that talks
them out of going, has failed at the one thing nothing else in the repo does for it.

Run the validator and record `summary` verbatim:

```bash
uv run --script .claude/skills/research-curator/scripts/validate_research.py main --json ./research/{category}/{name}.md
```

| Check | Defect when | Record |
|---|---|---|
| **Validator errors** | `summary.errors > 0` | Every error's `check`, `message`, `line`. An entry with errors should not have reached review — the Validation Gate holds it back — so report this and stop rather than continuing to Gate 2 |
| **Source URL present** | The entry names no canonical source URL — nothing in frontmatter (root or nested, e.g. `metadata.source_url`, `github_repository`), no `Source URL` text-header field, and no URL in References standing in for one | Read the entry for this rather than trusting the validator's `header_fields` warning, which only knows a fixed set of key spellings. Quote the URL you found, or record that none exists |
| **Source URL resolves** | `curl -sS -o /dev/null -w '%{http_code} %{url_effective}' -L --max-time 15 {source_url}` returns 4xx/5xx, or the host does not resolve | The status and the effective URL. A redirect to a live page passes — record the final URL as the required correction |
| **Verification date present** | The entry carries no date saying when the source was last read — no `last_verified`, `verified`, `research_date`, or text-header `Research Date` | Read the entry's own frontmatter or header block for this; the validator knows a narrower set of key spellings, so its `freshness_tracking` and `header_fields` warnings are a prompt to look, never the finding. Quote the date you found, or record that none exists. Without one the reader cannot tell how stale the pointer is |
| **No bare nonexistence claim** | "Doesn't support X", "Not available", "Not supported", "X is impossible" asserted about the subject | Quote it. Correction: Rule 3 language from [Entry Quality Standards](./entry-quality-standards.md) — "Not mentioned in {source}" / "Unable to access {source}". This is the one fidelity failure that survives: it tells the reader, on the writer's word, not to bother going to the source |

Every other validator warning and info item is **reported, not scored** — include the counts from
`summary` in the verdict block and move on.

---

## Gate 2 — Do the claims about this repository survive contact with it?

Scope: the entry's "Relevance to Claude Code Development" section and every proposal in the
`-improvements.md` and `-utilization.md` files the invocation named.

First, run the validator over each analysis file the invocation named:

```bash
uv run --script .claude/skills/research-curator/scripts/validate_research.py main --json {analysis-file-path}
```

Treat every `repo_path_unresolved` issue it reports as a confirmed step-2 defect below: record it and
do not re-derive it. That check reaches only existing-state assertions inside `research/insights/`
and `research/utilization/` — never the entry itself, and not every claim even in those files — so a
clean run means nothing was flagged mechanically, not that the claims are verified. Everything the
validator did not flag is judgment, below.

Then enumerate every claim the scoped text makes about **this** repository and walk the steps in
order, stopping at the first failure:

1. **Names something here** — the claim names a concrete path, skill, agent, command, or workflow of
   this repo. "Fits well with this project's architecture", "useful for agent workflows", "could
   improve code quality" fail here: they name nothing, so nothing can falsify them, and they would
   be equally true of any repository. A claim that survives a find-and-replace of this repo's name
   is a defect no matter how many sentences around it verify.
2. **Exists** — open the path. Not in the repo is a defect, full stop. Do not repair a near-miss on
   the writer's behalf; record what was named and what is actually there.
3. **Described correctly** — the file's real contents match what the claim says about them. Naming a
   real path and misdescribing it is the same severity as inventing one.
4. **Gap is real** — where the claim says this repo lacks a capability, the file confirms the
   absence. A capability the file already implements makes the claim a defect, not a weak proposal.
5. **Signal runs** — where the claim names a command or an observable field as its completion
   signal, run that command and read that field.

A claim about the **subject** that a repo claim rests on is checked too, against the source the entry
cites — a proposal to adopt a mechanism is a defect if the mechanism is not in the source. Subject
claims that no repo claim rests on are out of scope: the reader goes to the source for those.

Record each claim with the path you opened. A Gate 2 result asserts you opened the files; it cannot
be reached by reading the proposals alone.

---

## Verdict

```text
REVIEW: ./research/{category}/{name}.md

GATE 1 pointer:     PASS | FAIL | NOT RUN ({reason})
  validate_research main --json: errors {N}, warnings {N}, info {N}
  source URL: {url} — HTTP {status}
  verified: {date | absent}
GATE 2 repo claims: {N} claims checked, {N} defective | NOT RUN ({reason})
  repo_path_unresolved: {N}

DEFECTS: {N}
1. {file}:{line} — GATE {1|2} — "{exact quoted text}" — {required correction}
2. ...

VERDICT: USABLE | UNUSABLE | NOT RUN
```

`USABLE` when Gate 1 passes, whatever Gate 2 found. A live, dated pointer to the canonical source is
what this entry alone provides; a wrong proposal inside it is a repair to make, not a reason to
withhold the entry from the index.

`UNUSABLE` when Gate 1 fails. The entry points nowhere, so every claim in it rests on a subject the
reader cannot go and check. Re-source it with `--rerun`.

`NOT RUN` when Gate 1 could not run at all — the entry path does not exist, or this rubric could not
be loaded. Report the reason instead of a partial verdict.

Every recorded defect is a required repair regardless of verdict. `DEFECTS: 0` and `UNUSABLE` can
both be true; so can `DEFECTS: 9` and `USABLE`.
