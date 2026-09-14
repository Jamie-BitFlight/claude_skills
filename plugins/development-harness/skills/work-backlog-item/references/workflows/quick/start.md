# Quick Mode (Step Q)

**Trigger:** <route/> is `--quick`. Skips grooming, RT-ICA, and SAM planning. For one-file fixes, broken links, and typo patches where full pipeline overhead is disproportionate.

**Why skipping grooming is safe here**: a task and plan normally require gathering real detail —
scope, where the problem occurs, whether it's even true — before they exist. `--quick` skips
that gathering step, not the need for it. It's normally invoked mid-task, as an addendum to work
already in progress, so the invoking agent already has that context from its own session — it
already knows the scope and has already confirmed the problem, or it wouldn't have flagged it.
Step 1's `{observations}` is where that already-known context gets written down, not investigated
fresh. If the invoking agent doesn't actually have that context (a bare guess, not something it
confirmed while doing other work), `--quick` produces a task too thin to act on — that's a sign
the fix isn't actually trivial enough for this path, not something `--quick` itself can fix.

**Entry point from proactive fix routing:** When an agent's pre-fix check classifies a discovered
issue as trivial and routes it to --quick, the agent invokes this workflow as:
  /dh:work-backlog-item --quick {item title or #N}

If no backlog item exists for the fix, the agent does NOT call backlog_add first. Instead it
passes the descriptive title directly to `--quick`, which creates a minimal item inline (Step 2
of this workflow). The gate, not the user, authorizes the --quick routing decision.

**Invocation form:** `flags.quick = true` in the coerced input. Not a registry command. The raw
request is passed as `item_ref` — it can be a question, a bug report, or a fix ask; it does not
need to already read like a title (e.g. "why does login keep redirect-looping when SSO is
enabled" is a valid `item_ref`, not just "Login redirect loop").

1. From <item_ref/>, derive:
   - `{title}` — a short, title-shaped label of the symptom or request (this is what you would
     write as a backlog item title, not the raw request verbatim).
   - `{observations}` — verifiable facts about the circumstances the request arose in: what you
     were discussing or working on when it came in, what system/file/topic was in view, an exact
     error message, what's already been ruled out. Record what you actually observed, not what you
     infer the request means — a short or ambiguous request read without its surrounding context
     invites exactly the wrong guess (e.g. "which is the best beatle" asked mid-discussion of
     African dung beetles isn't a Ringo Starr question; the observation that grounds it is *what
     was being discussed*, not a reinterpretation of the request itself). This is not optional
     filler — a bare title strips the surrounding context a downstream reader needs to interpret
     the request correctly.

   Separately, scan `<item_ref/>` for an explicit `#N` issue reference (the `#` prefix required —
   a bare number is too ambiguous to treat as a reference here, since it may just be ordinary
   request content such as a port or line number). If found anywhere in the text, record it as
   `{explicit_ref}`, independent of whatever `{title}`/`{observations}` get derived from the same
   raw text — this survives even when other text follows it (e.g. `#42 -- Only fails with SSO` →
   `{explicit_ref}="#42"`), unlike SKILL.md's routing-layer `item_ref` discriminator, which only
   fires when a `#N` consumes the *entire* remaining text.

   Derive the same `{title}` for the same raw request as consistently as you can — prefer the most
   literal, shortest faithful label over creative rephrasing — since Step 2's lookup falls back to
   matching on `{title}` (after trying `{explicit_ref}` first, when captured) to avoid creating a
   duplicate on a repeat invocation. This is best-effort, not deterministic: `{title}` is derived,
   not parsed, so exact stability across separate invocations isn't guaranteed the way it would be
   for literal substring extraction — `{explicit_ref}`, when present, is the reliable match.

   If the title, or `{observations}`, states a cause for the problem (e.g. "X failing because Y",
   "X due to Y") that is not a confirmed observation, the persisted text must not assert it as fact
   either — the creation-time hypothesis-labeling rule (`create/scope.md`) applies here too, even
   though this path skips the rest of that workflow. Strip the causal clause from wherever it
   appears (title, `{observations}`, or both — check each independently) before any lookup or
   write, keeping only the symptom (e.g. "X failing"), and record every causal clause found as
   `{hypothesis}` (`**Hypothesis**: {cause}`, one line per clause if more than one) for use in the
   description if a new item is created. Build slug from the normalized title: lowercased, spaces
   → hyphens. Every step below — the lookup, `--slug`, selectors, reported handoffs — uses this
   normalized `{title}`/`{slug}`.

2. Find the item via the CLI. If Step 1 captured `{explicit_ref}`, try
   `backlog view --selector "{explicit_ref}"` first — this is the same item a plain `#42` lookup
   would find, just recovered from inside a longer request. If not found, or `{explicit_ref}`
   wasn't captured, fall back to `backlog view --selector "{title}"` (using the normalized
   `{title}` from Step 1). If neither lookup succeeds (JSON output contains an `error` key),
   create a minimal item:

   The backlog item's `description` starts as `{title}`, then appends each of `{observations}` and
   `{hypothesis}` that Step 1 recorded, each on its own paragraph, in that order
   (`{title}\n\n{observations}\n\n{hypothesis}` when both are present). With neither, the
   description matches the title exactly. This full description — hypothesis included — is the
   backlog item's own informational record; it is not what Step 4 uses as the task brief below.

   ```bash
   backlog add \
     --title "{title}" \
     --priority P2 \
     --description "{description from above}"
   ```

   Record `{item_title}` = `{title}` — the label just used to create it.

   If found (by either lookup in this step), extract description and acceptance criteria from the CLI's JSON output (`body`/`sections`) — this is the real content to use below, not just what was in `<item_ref/>` (e.g. `--quick #42` has almost nothing in the raw request itself; the existing item is where the actual problem statement lives). Record `{item_title}` = the fetched item's own `title` field — Step 4 uses this, not the derived `{title}` or `{task_brief}`, as `--task-title`.

3. Build `{task_brief}` for Step 4. A SAM task is an execution brief, not a groomed artifact, so it
   never carries `{hypothesis}`, labeled or not, from any source:
   - Item found in Step 2 (already existed): `{task_brief}` = the fetched description, with any
     line starting `**Hypothesis` removed if present — matching both the original
     `**Hypothesis**: {text}` marker and the refuted variant `**Hypothesis (refuted — see
     Fact-Check section)**: {text}` that `finalize.md`'s Hypothesis Resolution step writes (an
     existing item can carry either, same as a freshly-created one), plus acceptance criteria if
     available.
   - Item not found (just created in Step 2): `{task_brief}` = `{title}` plus `{observations}` from
     Step 1 — already excludes `{hypothesis}` by construction.

4. Create the quick plan via the CLI using `{task_brief}` for `--goal`, but `{item_title}` (not
   `{task_brief}`) for `--task-title` — `Task.title` is capped at 200 characters
   (`sam_schema/core/models.py`), and `{task_brief}` for an existing item can carry its full
   fetched description plus acceptance criteria, which routinely exceeds that. `{item_title}` is
   always short by construction (it's a backlog item title). If `{item_title}` still exceeds 200
   characters, truncate to 200:

   ```bash
   plan create \
     --slug "quick-{slug}" \
     --goal "{goal from task_brief or acceptance_criteria}" \
     --task-id T1 \
     --task-title "{item_title}" \
     --task-agent "task-worker" \
     --task-priority 1 \
     --task-complexity low
   ```

   `plan create` accepts only one inline task per call (use `plan append-task` for additional
   tasks) — sufficient here since the quick plan is always single-task. It handles path resolution
   internally — do not resolve or pass a file path. Read `plan_id` (e.g. `Pe71c7cb8-{slug}`) from the JSON
   output — that is the plan reference used in the next two steps, not the `quick-{slug}` string.

5. Call the CLI to record the plan reference: `backlog update --selector "{item_title}" --plan "{plan_id from step 4}"` — use `{item_title}` here too, since that's the selector guaranteed to resolve to the item Step 2 actually found or created (an existing item's real title can differ from Step 1's re-derived `{title}` guess).

6. Report the `plan_id` returned by `plan create`:

   ```text
   Quick plan created: {plan_id from step 4}
   Steps: {N} tasks

   To execute: /dh:implement-feature {plan_id}
   To close:   /dh:work-backlog-item close {item_title}
   ```
